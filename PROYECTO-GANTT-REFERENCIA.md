# ADO Gantt Chart — Referencia del Proyecto

## Archivo principal
`/Users/matiaslazarte/Cloude_1/ado-gantt.html` — 1000 líneas, todo en un solo archivo HTML/CSS/JS

## Cómo ejecutar
```bash
python3 -m http.server 8080 --directory ~/Cloude_1
# Abrir: http://localhost:8080/ado-gantt.html
```

## Configuración inicial (overlay al abrir)
- Organización ADO
- Proyecto ADO
- PAT (Personal Access Token) con permisos Work Items Read + Project/Team Read
- Se guarda en `localStorage`

---

## Estructura del árbol
```
Epic → Feature → User Story / Technical Task / Improvement → Task / Bug
```
- Colapsado por defecto al cargar
- `collapsed` es un `Set` de IDs
- `TYPE_ORDER = { Epic:0, Feature:1, User Story:2, Technical Task:2, Improvement:2, Task:3, Bug:4 }`

## Jerarquía de fecha por tipo
- **Epic**: StartDate + TargetDate (campo ADO). Fallback: sprint si tiene iteración
- **Feature**: StartDate + TargetDate. Fallback: sprint
- **User Story / Technical Task / Improvement / Task / Bug**: fechas del sprint (iteración)

## Sprints
14 sprints hardcodeados (Evolutivo team) — se usan como prioridad 1:
```
Sprint 1:  16/03/2026 – 27/03/2026
Sprint 2:  30/03/2026 – 10/04/2026
Sprint 3:  13/04/2026 – 24/04/2026
Sprint 4:  27/04/2026 – 08/05/2026
Sprint 5:  11/05/2026 – 22/05/2026
Sprint 6:  25/05/2026 – 05/06/2026
Sprint 7:  08/06/2026 – 19/06/2026
Sprint 8:  22/06/2026 – 03/07/2026
Sprint 9:  06/07/2026 – 17/07/2026
Sprint 10: 20/07/2026 – 31/07/2026
Sprint 11: 03/08/2026 – 14/08/2026
Sprint 12: 17/08/2026 – 28/08/2026
Sprint 13: 31/08/2026 – 11/09/2026
Sprint 14: 14/09/2026 – 25/09/2026
```

Formato de iteración en ADO: `"probatch\Sprint 5 - Evolutivo."` (backslash, trailing period)

## Filtrado por equipo
- Dropdown en topbar
- Llama a `teamsettings/teamfieldvalues` para obtener area paths del equipo
- Agrega cláusula `AND [System.AreaPath] UNDER '...'` al WIQL

## WIQL — tipos incluidos
`Epic, Feature, User Story, Technical Task, Task, Bug, Improvement`

## Estados excluidos
`Removed, Cut, Cancelled, Rejected, Withdrawn`

## Progreso
- Leaf nodes: `stateToProgress(state)` → 0 / 50 / 100 según estado
- Nodos con hijos: promedio recursivo bottom-up (`calcProgress`)
- Estados "done": done, closed, resolved, completed, inactive
- Estados "in progress": active, in progress, committed, in review, code review

---

## Variables de estado principales
```javascript
let cfg = {};           // config guardada en localStorage
let teams = [];
let selectedTeam = '';
let iterations = [];
let workItems = [];
let collapsed = new Set();
let activeTypes = new Set(['Epic','Feature','User Story','Technical Task','Task','Bug','Improvement']);
let DAY_W = 28;         // px por día en el timeline
let tlStart = null;     // Date inicio del timeline
let tlDays = 0;
let lastRaw = [];
let currentAreaFilter = '';
let nameColW = 220;     // ancho columna nombre (resizable via drag)
let fullTree = [];
```

## CSS clave
- `.lh` / `.l-row`: `grid-template-columns: var(--name-col) 95px 72px 145px`
- `--name-col`: CSS variable, cambia con el drag del handle
- `.sprints-row`: `position: relative; height: 65px`
- `.sprint-cell`: `position: absolute` (coordenadas absolutas, mismo sistema que las barras)
- `.g-row`: `height: 40px`

## Timezone fix (Argentina UTC-3)
```javascript
function parseAdoDate(str) {
  const m = String(str).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return new Date(str);
  return new Date(+m[1], +m[2] - 1, +m[3], 12, 0, 0);  // mediodía local
}
```

## Scroll preservation al colapsar/expandir
```javascript
function toggleCol(id) {
  const tl = document.getElementById('tlScroll');
  const savedScroll = tl ? tl.scrollLeft : 0;
  collapsed.has(id) ? collapsed.delete(id) : collapsed.add(id);
  render.skipScroll = true;
  render();
  initResizeHandle();
  document.getElementById('tlScroll').scrollLeft = savedScroll;
}
```

---

## Pendientes / issues conocidos al cerrar sesión
- **Sort de Épicas**: el usuario quiere que "Transversal" aparezca después de "Fase 4". El sort actual es por TYPE_ORDER y luego localeCompare. Falta implementar orden personalizado para épicas específicas.
- **Progreso**: implementado con estado (0/50/100%) y promedio bottom-up. Columna visible en UI.
- **findIter()**: matching de iteration path robusto (sprint number, case-insensitive, trailing period removal). Puede haber edge cases.

## Chips de filtro de tipo
En topbar: Epic, Feature, Story, Tech Task, Task, Bug, Improvement — togglean `activeTypes`
