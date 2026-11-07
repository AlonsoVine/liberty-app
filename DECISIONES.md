# Mejora estética de Liberty — decisiones

Rama: `mejora-estetica` (repo **liberty-app**, carpeta local `rumboExito`). La web oficial
(`liberty`, landing de GitHub Pages) queda fuera de esta tarea.

## 1. Inspección inicial (7-nov-2026)

| Aspecto | Hallazgo |
|---|---|
| Stack | Python 3.10+ · Flask (servidor local en `127.0.0.1:8765`) · front HTML/CSS/JS **nativo, sin build ni dependencias JS**. |
| Estructura front | `app/web/index.html` (≈2630 líneas: **todo el CSS** va en un único `<style>` de ≈1770 líneas + el marcado de las pestañas), `app.js` (≈4800, panel), `editor.js` (≈4870, «Mis datos» y «Documentos»), `graficos.js` (≈1260, gráficos SVG propios), `cargador.js`, `canal.js`. |
| Sistema de estilos | Tokens en `:root` (superficies `--plano/--sup/--sup2/--sup3`, tintas `--tinta/2/3`, estados `--bien/--mal/--aviso`, 24 colores de serie `--s1…--s24`, `--radio`, duraciones `--dur-1/2/3`, curvas `--ease`). Dos temas: **oscuro** (por defecto) y **claro** (`html[data-tema]`), más «auto». Tipografía del sistema (`system-ui`/Segoe UI). Ya respeta `prefers-reduced-motion` (CSS global + `window.SIN_MOV` en JS). |
| Iconografía | **Emojis como iconos** en barra superior, pestañas, tarjetas de Inicio, avisos y paleta de búsqueda. Solo el «ojo» de privacidad es SVG. |
| Cómo se ejecuta | `python -m app` (`.venv` del repo principal); `PATRIMONIO_NO_ABRIR=1`, `LIBERTY_PUERTO`, `PATRIMONIO_DATOS` para aislar. Empaquetado: PyInstaller (`Liberty.spec` incluye `app/web` entera), Docker (`Dockerfile`, excluye `docs/`). |
| Offline | La app es **100 % local**; no puede depender de CDNs. CSP: `default-src 'self'`, `style-src 'self' 'unsafe-inline'`, `script-src 'self'`. |
| Exportación | `app/exportar.py` genera un HTML autónomo a partir de `index.html` (inyecta los JS en línea). Cualquier recurso nuevo referenciado por URL relativa debe ir también incrustado ahí. |
| Tests / checks existentes | `pytest` (suite en `tests/`, en verde) y `npm test` (30 tests jsdom en `tests-js/render.test.js`, en verde). CI: ruff + pytest. No hay build de front. |

### Línea base de checks objetivos (antes de tocar nada)
- Consola: **0** errores/avisos.
- Scroll horizontal: **sí**, a 360 y 390 px en Distribución, Rentabilidad y Evolución.
- axe-core (WCAG 2 A/AA): contraste insuficiente (gris `--tinta3` en tema claro 3,4:1; sub-pestañas en oscuro 4,38:1; texto blanco sobre azul primario 3,63:1), ARIA mal formado en las sub-pestañas del Panel (`aria-selected` en botones sin `role="tab"`), botones Ayuda/Ajustes con `role="tab"` fuera de un `tablist`, `select` y `input` sin nombre accesible, región desplazable no enfocable.
- Foco visible: correcto en los 30 primeros tabuladores.
- Lighthouse: ver `REVISIONES.md`.

## 2. Decisiones de método

- **Worktree aparte.** `main` tenía trabajo sin commitear (patrimonio de ejemplo integral, ADR 0037). Para no tocar `main` ni ese trabajo, la rama `mejora-estetica` sale de `main` (commit `a47c1ec`) en un *worktree* hermano (`../rumbo-estetica`). Así el árbol de trabajo de `main` queda intacto y el futuro merge solo choca, como mucho, en textos de ayuda que no toco.
- **Datos de las capturas.** La app se lanza con una carpeta de datos vacía y aislada, así que muestra el **patrimonio de ejemplo de la primera vez** (solo lectura). Se marcan como vistas la bienvenida y el tour (localStorage) para capturar las pantallas limpias. Capturas con `reduced_motion` para que sean deterministas (sin contadores a medias).
- **Capturas.** Playwright + Chromium (instalación del sistema, fuera del proyecto). 12 pantallas + paleta de búsqueda × 390/768/1440 px × oscuro/claro, en `docs/estetica/capturas/<vuelta>/` (JPEG, `docs/` no se empaqueta ni entra en Docker).
- **Herramientas de auditoría** (Lighthouse, axe-core) instaladas **fuera del repo** (scratchpad); no son dependencias del proyecto.
- **Criterio de «animación solo transform/opacity».** Las animaciones de entrada, salida y cambio de estado se hacen solo con `transform` y `opacity`. Las animaciones existentes que movían propiedades de layout (`width` de barras de progreso, `grid-template-rows` de la caja de avisos, `left/top` del foco del tour) se reescriben. Los fundidos de **color** en hover/foco (`color`, `background-color`, `border-color`) se mantienen: no provocan layout, son baratos y son el lenguaje habitual de estado; se documenta como excepción explícita.

## 3. Decisiones de diseño

(Se completa en cada vuelta.)
