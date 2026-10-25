# ADR 0024 — Rango de fechas en Ingresos y gastos, tooltip «Total», licencia propia y Mac universal2

- **Estado:** aceptado
- **Fecha:** 2026-10-25
- **Fase:** madurez de UX + identidad propia (versión 1.15.0)

## Contexto

Tanda pedida por Alonso: poder analizar los ingresos y gastos en el rango de fechas que uno
quiera (no solo «este mes»), completar la información del gráfico de evolución en la vista
«Total», corregir el icono de calendario invisible en modo oscuro, y dar a Liberty identidad
propia separándolo de «Rumbo» (README atractivo sin referencias a Rumbo/Dani y licencia más
privativa). Además, resolver la distribución en Mac con un único instalador que funcione tanto
en Apple Silicon como en Intel, ya que los runners macos-13 (Intel) de GitHub apenas tienen
disponibilidad.

## Decisiones

**1. Control de periodo en Ingresos y gastos (`app.js`, `index.html`).** Nuevo selector
`#igPeriodo` encima del panel con **Este mes · Año · 12 meses · Rango…** (rango personalizado
desde→hasta). Gobierna **Resumen** (KPIs ingresos/gastos/ahorro/tasa + cascada «¿a dónde fue el
dinero?») y **Categorías** (donut/ranking + «por titular»). Se calcula en el cliente a partir de
`D.flujosLista` (`ventanaPeriodo`, `listaFlujosFiltrada`, `agregaRango`, `datosPeriodo`), por lo
que admite cualquier rango y respeta los filtros propios del panel (titular/entidad/marca/
dimensión). El modo se recuerda (`recuerda` → `patrimonio.igPeriodo`). Si la cartera no tiene
`flujosLista`, cae al comportamiento anterior (este mes / 12 meses). **Tendencias** y
**Presupuesto** no lo usan (son mensuales por naturaleza).

**2. No duplicar el «Periodo» global (`app.js`, `pintaPatrimonio`).** El panel ya tenía un
control de periodo global (`pintaMesReferencia`, `#mesReferencia`) que recalcula el patrimonio a
una fecha / tramo. En la vista de Ingresos y gastos ese control **no** afecta a las cifras de
ingresos/gastos (que las manda `igPeriodo`), así que se oculta ahí —junto con la tarjeta «del
tramo» `#resultadoPeriodo`— con la misma mecánica `ocultoInicio` que ya se usaba en «Inicio».
El filtro de titular/dimensión sí se mantiene (alimenta `listaFlujosFiltrada`).

**3. Tooltip enriquecido de la evolución «Total» (`graficos.js`, `app.js`).** `lineaConEventos`
admite `cfg.rentabilidadTT`: cuando está activo (solo lo pasa la vista «Total», `cfgL`), al pasar
el ratón el detalle muestra **aportado · plusvalía (valor − aportado, coloreada) · rentabilidad %
· inflación** (si `overlay2` está presente), en vez de solo el aportado. El resto de llamadas
(proyección, ficha de fondo) no pasan el flag y conservan el tooltip simple.

**4. Icono de calendario visible en modo oscuro (`index.html`).** Los `input[type=date]` con
fondo oscuro propio anulaban el auto-oscurecido del glifo del navegador. Se fuerza
`color-scheme:light` en todos ellos (glifo oscuro determinista) y, en tema oscuro, se invierte el
`::-webkit-calendar-picker-indicator` (`filter:invert(1) brightness(1.75)`), de modo que el icono
resalta en cualquier tema.

**5. Identidad propia: README y licencia (`README.md`, `LICENSE`).** El README se reescribe con
marca Liberty, sin referencias a Rumbo/Dani/YouTube, con el modelo real de distribución
(Liberty.exe / .dmg desde la landing) y las funcionalidades actuales. La licencia pasa a ser
**híbrida**: sección 1 = aviso MIT de la obra original «Rumbo» (Dani Dominguez Quant), que no se
puede revocar; sección 2 = **todos los derechos reservados** sobre las aportaciones de Liberty
(Alonso), con uso personal permitido y sin copia/modificación/redistribución/uso comercial sin
permiso escrito. La atribución a Dani se mantiene en la LICENSE y en el «Acerca de» de la app.

**6. Mac: un único .dmg universal2 (`build-mac.yml`, `Liberty-mac.spec`).** Se deja de construir
dos .dmg (Apple Silicon + Intel) y se construye **uno solo universal2** (arm64 + x86_64 en el
mismo binario) en `macos-14`. Como `actions/setup-python` da un Python de una sola arquitectura,
se instala el **Python universal2 de python.org**; la única extensión C (`markupsafe._speedups`)
se compila desde fuente con `ARCHFLAGS="-arch x86_64 -arch arm64"`; y `Liberty-mac.spec` fija
`target_arch` desde `LIBERTY_TARGET_ARCH` (universal2 en el workflow, `None` en un build local de
una sola arquitectura). El asset pasa a llamarse **`Liberty-macOS.dmg`** (una sola descarga de
Mac). El contador de la landing sigue sumando los assets antiguos (`Liberty-macOS.zip`,
`-AppleSilicon.dmg`, `-Intel.dmg`).

## Retrocompatibilidad

Todo aditivo. Carteras sin `flujosLista` siguen funcionando (fallback de periodo). El tooltip
simple se conserva donde no se pide el enriquecido. La licencia nueva no revoca la MIT de la obra
original. El build local de Mac de una sola arquitectura sigue igual (sin `LIBERTY_TARGET_ARCH`).

## Tests

`ruff` (OK), `node --check` en los tres JS (OK), `npm test` 14/14 (OK), `pytest` 244 (OK), y
verificación por CDP en vivo: control de periodo en Resumen y Categorías con rango personalizado
(«del 1/11/25 al 31/10/26»), icono de calendario visible en oscuro, y tooltip «Total» con
aportado + plusvalía + rentabilidad % + inflación. El build universal2 se valida en el runner con
`lipo -archs` (Python, `markupsafe._speedups` y el ejecutable final deben listar `x86_64 arm64`).
