#!/usr/bin/env python3
"""
Robot — AST Time Report
Carga automáticamente las horas del día en:
https://timereport.accusys.com.ar/web/login.aspx

Uso:
  python3 timereport_bot.py              → carga 8 horas hoy (con ventana visible)
  python3 timereport_bot.py --horas 6   → carga 6 horas hoy
  python3 timereport_bot.py --auto       → guarda sin pedir confirmación
  python3 timereport_bot.py --headless   → sin ventana (para cron)
"""

import asyncio
import argparse
import sys
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ─────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────
URL_LOGIN   = "https://timereport.accusys.com.ar/web/login.aspx"
USERNAME    = "matias.lazarte"
PASSWORD    = "Accusys02$"
HORAS_DIA   = 8      # horas a cargar por defecto
ACTIVIDAD_ID = "121431"   # ID de la actividad a seleccionar
ACTIVIDAD_LABEL = "STAFF ACCUSYS_ING DE PRODUCTO Y SERV_Desarrollo de Prod. PROBATCH"


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def ok(msg):   print(f"  ✓  {msg}")
def info(msg): print(f"  →  {msg}")
def warn(msg): print(f"  ⚠  {msg}")
def err(msg):  print(f"  ✗  {msg}")


async def esperar_selector(page, selector, timeout=10000):
    """Espera a que un selector exista y sea visible."""
    try:
        await page.wait_for_selector(selector, state="visible", timeout=timeout)
        return True
    except PlaywrightTimeout:
        return False


async def seleccionar_actividad(page, actividad_id: str, actividad_label: str):
    """
    Selecciona la actividad en el dropdown.
    Busca por ID numérico (ej: 121431) o por texto parcial.
    """
    # Buscar el select de Actividad por distintos IDs
    for selector in [
        "select[id*='Actividad' i]",
        "select[id*='Activity' i]",
        "select[name*='Actividad' i]",
    ]:
        sel = page.locator(selector)
        if await sel.count() > 0:
            options = await sel.locator("option").all_text_contents()
            # Buscar opción que contenga el ID
            for opt in options:
                if actividad_id in opt:
                    await sel.select_option(label=opt)
                    ok(f"Actividad seleccionada: {opt.strip()[:60]}…")
                    await asyncio.sleep(0.8)  # esperar que se recargue el proyecto
                    return True

    # Fallback: recorrer todos los selects
    selects = page.locator("select")
    count = await selects.count()
    for i in range(count):
        sel = selects.nth(i)
        options = await sel.locator("option").all_text_contents()
        for opt in options:
            if actividad_id in opt or actividad_label[:20] in opt:
                await sel.select_option(label=opt)
                ok(f"Actividad seleccionada: {opt.strip()[:60]}…")
                await asyncio.sleep(0.8)
                return True

    warn(f"No se encontró la actividad {actividad_id}. Verificá manualmente.")
    return False


async def seleccionar_horas(page, horas: int):
    """
    Selecciona el valor en el dropdown de Horas.
    Prueba múltiples estrategias dado que es ASP.NET WebForms.
    """
    # Opción 1: buscar select que contenga "hs" en sus opciones
    selects = page.locator("select")
    count = await selects.count()

    for i in range(count):
        sel = selects.nth(i)
        options = await sel.locator("option").all_text_contents()
        # Buscar la opción que corresponde a las horas deseadas
        target = None
        for opt in options:
            if f"{horas} hs" in opt and "0 min" in opt:
                target = opt
                break
        if target:
            await sel.select_option(label=target)
            ok(f"Horas seteadas: {target}")
            return True

    # Opción 2: buscar por ID parcial
    for id_fragment in ["Horas", "Hours", "hora"]:
        locator = page.locator(f"[id*='{id_fragment}' i]")
        if await locator.count() > 0:
            options = await locator.first.locator("option").all_text_contents()
            for opt in options:
                if f"{horas} hs" in opt:
                    await locator.first.select_option(label=opt)
                    ok(f"Horas seteadas: {opt}")
                    return True

    # Fallback JS: buscar via JavaScript el select que tenga opciones con " hs"
    result = await page.evaluate(f"""
        (function() {{
            var selects = document.querySelectorAll('select');
            for (var i = 0; i < selects.length; i++) {{
                var opts = selects[i].options;
                for (var j = 0; j < opts.length; j++) {{
                    if (opts[j].text.indexOf(' hs') !== -1 && opts[j].text.indexOf(' min') !== -1) {{
                        // Buscar la opción de {horas} horas 0 min
                        for (var k = 0; k < opts.length; k++) {{
                            if (opts[k].text.indexOf('{horas} hs') !== -1 && opts[k].text.indexOf('0 min') !== -1) {{
                                selects[i].value = opts[k].value;
                                selects[i].dispatchEvent(new Event('change', {{ bubbles: true }}));
                                return opts[k].text;
                            }}
                        }}
                    }}
                }}
            }}
            return null;
        }})()
    """)
    if result:
        ok(f"Horas seteadas (JS): {result}")
        return True

    warn("No se encontró el dropdown de horas. Configuralo manualmente.")
    return False


async def set_fecha_js(page, field_id: str, fecha: str):
    """Usa JS para cambiar un campo readonly y disparar el evento onchange."""
    await page.evaluate(f"""
        var el = document.getElementById('{field_id}');
        if (el) {{
            el.removeAttribute('readonly');
            el.value = '{fecha}';
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
    """)
    # Esperar a que el servidor recargue el formulario tras el cambio de fecha
    await asyncio.sleep(1.5)
    await page.wait_for_load_state("networkidle")


async def verificar_fecha(page, fecha_esperada: str):
    """Verifica y corrige la fecha. Maneja campos readonly via JS."""
    # Primero intentar por ID conocido (txtFechaDesde / txtFecha)
    for known_id in ["txtFechaDesde", "txtFecha", "Fecha"]:
        val = await page.evaluate(f"""
            var el = document.getElementById('{known_id}');
            el ? el.value : null;
        """)
        if val and "/" in val and len(val) == 10:
            if val != fecha_esperada:
                info(f"Fecha actual: {val} → corrigiendo a {fecha_esperada}")
                await set_fecha_js(page, known_id, fecha_esperada)
            else:
                ok(f"Fecha correcta: {val}")
            return True

    # Fallback: buscar cualquier input con fecha via JS
    result = await page.evaluate(f"""
        (function() {{
            var inputs = document.querySelectorAll('input[type="text"], input:not([type])');
            for (var i = 0; i < inputs.length; i++) {{
                var v = inputs[i].value;
                if (v && v.indexOf('/') !== -1 && v.length === 10) {{
                    return {{ id: inputs[i].id, value: v }};
                }}
            }}
            return null;
        }})()
    """)
    if result:
        if result['value'] != fecha_esperada:
            info(f"Fecha actual: {result['value']} → corrigiendo a {fecha_esperada}")
            if result['id']:
                await set_fecha_js(page, result['id'], fecha_esperada)
            else:
                warn("Campo de fecha sin ID — no se pudo corregir")
                return False
        else:
            ok(f"Fecha correcta: {result['value']}")
        return True

    warn("No se encontró campo de fecha — continuando de todas formas")
    return False


# ─────────────────────────────────────────────
#  FLUJO PRINCIPAL
# ─────────────────────────────────────────────
async def run(horas: int, auto_save: bool, headless: bool = False, fecha: str = None):
    today = fecha if fecha else datetime.now().strftime("%d/%m/%Y")

    print()
    print("═" * 50)
    print("  🤖  AST Time Report Bot")
    print(f"  📅  Fecha: {today}")
    print(f"  ⏱   Horas a cargar: {horas} hs")
    print("═" * 50)
    print()

    async with async_playwright() as pw:
        # Lanzar Chrome (headless para cron, visible para uso manual)
        browser = await pw.chromium.launch(
            headless=headless,
            args=[] if headless else ["--start-maximized"]
        )
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # ── PASO 1: Login ──────────────────────────────
        info(f"Navegando a {URL_LOGIN}")
        await page.goto(URL_LOGIN, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")

        # Llenar usuario
        user_selectors = [
            "input[id*='User' i]",
            "input[name*='User' i]",
            "input[type='text']:first-of-type",
        ]
        user_filled = False
        for sel in user_selectors:
            if await esperar_selector(page, sel, timeout=3000):
                await page.fill(sel, USERNAME)
                user_filled = True
                break

        if not user_filled:
            err("No se encontró el campo de usuario.")
            input("Ingresá el usuario manualmente y presioná ENTER...")

        # Llenar contraseña
        pass_selectors = [
            "input[type='password']",
            "input[id*='Pass' i]",
            "input[name*='Pass' i]",
        ]
        pass_filled = False
        for sel in pass_selectors:
            if await esperar_selector(page, sel, timeout=3000):
                await page.fill(sel, PASSWORD)
                pass_filled = True
                break

        if not pass_filled:
            err("No se encontró el campo de contraseña.")
            input("Ingresá la contraseña manualmente y presioná ENTER...")

        # Click en Ingresar
        btn_selectors = [
            "input[value*='Ingresar' i]",
            "button:has-text('Ingresar')",
            "input[type='submit']",
            "input[type='button'][value*='Ingres' i]",
        ]
        btn_clicked = False
        for sel in btn_selectors:
            try:
                if await page.locator(sel).count() > 0:
                    await page.click(sel)
                    btn_clicked = True
                    break
            except Exception:
                continue

        if not btn_clicked:
            input("Hacé click en 'Ingresar' manualmente y presioná ENTER...")

        await page.wait_for_load_state("networkidle")
        ok("Login OK")

        # Screenshot para debug
        screenshot_path = "/Users/matiaslazarte/Cloude_1/logs/debug_post_login.png"
        await page.screenshot(path=screenshot_path)
        info(f"Screenshot guardado en: {screenshot_path}")

        # ── PASO 2: Seleccionar actividad ─────────────
        info(f"Seleccionando actividad {ACTIVIDAD_ID}...")
        await asyncio.sleep(1)
        await seleccionar_actividad(page, ACTIVIDAD_ID, ACTIVIDAD_LABEL)

        # ── PASO 3: Verificar fecha ────────────────────
        info("Verificando fecha...")
        await asyncio.sleep(0.5)
        fecha_ok = await verificar_fecha(page, today)
        if not fecha_ok:
            warn(f"No se pudo verificar la fecha. Asegurate de que sea {today}")

        # ── PASO 4: Seleccionar horas ──────────────────
        info("Seleccionando horas...")
        await asyncio.sleep(0.5)
        await seleccionar_horas(page, horas)

        # ── PASO 5: Confirmar y guardar ────────────────
        print()
        print("─" * 50)

        if not auto_save:
            print("  👀  Revisá el formulario en el navegador.")
            print("      Presioná ENTER para guardar o Ctrl+C para cancelar.")
            print("─" * 50)
            try:
                input()
            except KeyboardInterrupt:
                print()
                warn("Operación cancelada por el usuario.")
                await browser.close()
                sys.exit(0)
        else:
            info("Modo automático: guardando en 3 segundos...")
            await asyncio.sleep(3)

        # Click en Guardar
        guardar_selectors = [
            "input[value*='Guardar' i]",
            "button:has-text('Guardar')",
            "input[type='submit'][value*='Guardar' i]",
        ]
        saved = False
        for sel in guardar_selectors:
            try:
                if await page.locator(sel).count() > 0:
                    await page.click(sel)
                    saved = True
                    break
            except Exception:
                continue

        if saved:
            await page.wait_for_load_state("networkidle")
            ok("¡Horas guardadas correctamente!")
        else:
            warn("No se encontró el botón Guardar. Hacelo manualmente.")
            input("Presioná ENTER cuando hayas guardado...")

        # Esperar un poco antes de cerrar
        await asyncio.sleep(2)
        await browser.close()
        print()
        print("═" * 50)
        print("  ✅  Listo!")
        print("═" * 50)
        print()


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Robot para cargar horas en AST Time Report"
    )
    parser.add_argument(
        "--horas", type=int, default=HORAS_DIA,
        help=f"Horas a cargar (default: {HORAS_DIA})"
    )
    parser.add_argument(
        "--auto", action="store_true",
        help="Guardar automáticamente sin pedir confirmación"
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Correr sin ventana (ideal para cron/tareas programadas)"
    )
    parser.add_argument(
        "--fecha", type=str, default=None,
        help="Fecha a cargar en formato dd/mm/yyyy (por defecto: hoy)"
    )
    args = parser.parse_args()

    # En modo headless forzamos auto_save también
    auto = args.auto or args.headless

    try:
        asyncio.run(run(args.horas, auto, args.headless, args.fecha))
    except KeyboardInterrupt:
        print()
        warn("Interrumpido.")
        sys.exit(0)


if __name__ == "__main__":
    main()
