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

### Dirección: «banca privada editorial»
Se conserva la identidad (neutros cálidos `#0d0d0d / #f9f9f7`, azul de marca, paleta de series de datos, tema oscuro por defecto, densidad de cuadro de mando). Lo que se sube de nivel es la **voz tipográfica**, la **coherencia de la iconografía**, la **jerarquía de superficies** y el **movimiento**. No se toca contenido ni funcionalidad.

### Tipografía (vuelta 1)
- **Geist** (variable, OFL, 29 KB, subconjunto latino con €, ñ, ¿, «») para interfaz y cifras. Tiene `tnum`: las cifras de los contadores animados no bailan de ancho. Sustituye a `system-ui`, que en Windows es Segoe UI (la tipografía por defecto que el encargo pide evitar).
- **Fraunces** (variable con eje óptico, OFL, 66 KB) solo para titulares de sección y de modales. Da el tono cálido y personal que ya tenía el texto («Tu patrimonio», «Tu libertad financiera») sin restar legibilidad a los datos. Se descartó usarla en cifras: no tiene cifras tabulares y el contador animado saltaría de ancho.
- Las cifras grandes pasan de pesos 800 con resplandor a 600–640 con tracking negativo: más precisas y menos «HUD de videojuego».
- Dependencia nueva justificada: son **recursos** (no librerías), se sirven desde `app/web/fuentes/` (funciona sin conexión y cumple la CSP `default-src 'self'`), y la web exportada las incrusta en base64 (`app/exportar.py`). Licencias junto a los archivos.

### Iconos (vuelta 1)
- Juego propio de iconos de línea (24×24, trazo 1,75, extremos redondos, `currentColor`) en `app.js` (`ICO` / `ico()`), y en línea en el HTML estático de la barra. Sustituye a los emojis que hacían de **icono** (barra, pestañas, tarjetas de Inicio, avisos, paleta, filtros). Los emojis que son **contenido** (textos de ayuda, marcas que elige el usuario, notas) no se tocan.
- `ico()` acepta el emoji antiguo y devuelve su icono: así las plantillas apenas cambian y no se pierde ningún caso.

### Color y contraste (vuelta 1)
- Oscuro: `--tinta3 #898781 → #a09e95`, `--s1 #3987e5 → #5a9cf0` (texto azul ≥ 4,5:1 sobre todas las superficies).
- Claro: `--tinta3 → #5f5e58`, `--tinta2 → #45443f` (para mantener la distancia entre niveles), `--s1 → #1d63bd`, `--aviso → #8f6400`, `--mal → #c42f2f`.
- Nuevo `--acento-fondo` para rellenos con texto blanco (botón principal, web oficial): ≥ 5:1.
- La serie 1 de los gráficos usa `--s1`, así que su azul cambia ligeramente; es el mismo tono de marca, más luminoso en oscuro y más profundo en claro.

### Superficies (vuelta 1)
- En oscuro las sombras no se ven: las tarjetas pasan a borde fino + brillo superior de 1 px (`--brillo`). En claro, sombra difusa y baja.
- Celdas internas (libertad, constancia, tiles de Inicio, filas) tonales y sin borde duro, para quitar la sensación de «tarjeta dentro de tarjeta» y de tarjetas idénticas.
- Iconos dentro de una ficha tonal del color de su significado (azul, verde «ok», rojo «aviso»).

### Navegación y móvil (vuelta 1)
- Pestañas principales: subrayado que crece desde el centro con `transform: scaleX`.
- Barra superior en una sola fila hasta 360 px (los botones con texto pasan a solo icono y conservan `aria-label`); la fecha se oculta por debajo de 1100 px.
- Sub-pestañas del Panel: por debajo de 1180 px son un carril deslizable con desvanecido en el borde, y la activa se centra sola (`centraSubtab`). Antes se partían en 3–4 filas de cajas.
- Los controles segmentados largos se deslizan dentro de su ancho: era la causa del scroll horizontal a 360–390 px.

### Movimiento (vuelta 1)
- Entrada escalonada de los bloques al cambiar de vista y en la primera pintura (`.entrando`, 55 ms entre bloques, `translateY(10px)` + opacidad).
- Barras de progreso: de `width` a `translateX` sobre una pista con `overflow:hidden` (el remate redondeado se conserva y el «faro» queda dentro).
- Caja de avisos: de `grid-template-rows` a mostrar/ocultar + fundido del contenido. Interruptor: de `left` a `translateX`. Foco del tour: sin animar `left/top/width/height`.
- `prefers-reduced-motion`: se mantiene la regla global existente y el JS no aplica la entrada escalonada.

### Estabilidad (vuelta 1)
- CLS 0,97 → 0: el margen del primer aviso colapsaba hacia fuera del contenedor y, al aparecer el banner del ejemplo, toda la página bajaba. Ahora `body > .env` es `flow-root` y su contenido se muestra (con la entrada escalonada) cuando ya está pintado con los datos; si algo fallara, se muestra igualmente a los 2,5 s.

## Decisiones de la vuelta 2 (tras el árbitro 1)

### Movimiento estricto: solo `transform` y `opacity`
- Regla de sistema `*,*::before,*::after{transition-property:transform,opacity !important}`. Los cambios de color, fondo y borde en hover o foco pasan a ser instantáneos y nítidos, que en una herramienta de uso diario es lo más legible. Lo que se anima es desplazamiento, escala y opacidad.
- **Cambio de tema:** lo funde la View Transitions API (`document.startViewTransition`), que funde dos instantáneas por opacidad en 0,32 s. Sustituye a la clase `temaAnim`, que animaba colores. Con menos movimiento, o en navegadores sin la API, el cambio es directo.
- **Elevación en hover:** la sombra vive en un `::after` y aparece con opacidad, en vez de animar `box-shadow`.
- **Otras animaciones:**
  - Barra de carga: de `left` a `translateX`.
  - Destello del calendario: anillo en `::after` que late con opacidad.
  - `.metaFill`: sin transición de anchura.
- **Entrada escalonada:** 0,3 s con 28 ms entre bloques; antes era ~1 s. Es una herramienta de consulta diaria y el movimiento debe orientar, no hacer esperar.

### Momento firma: odómetro de cifras
- Las cifras protagonistas (patrimonio del héroe y de Inicio) ruedan dígito a dígito como un contador mecánico. Cada dígito es una columna 0–9 en un `::after` que se desplaza con `translateY`, con un retardo de 45 ms por posición.
- Encaja con la marca: es un libro de cuentas que «hace la suma».
- Cuesta 0 dependencias. Vuelve a texto plano a los 2,2 s para copiar y pegar y para los lectores de pantalla.
- Con menos movimiento, la cifra aparece directamente.

### Iconos: iconizador central
- En lugar de perseguir cada plantilla, un `MutationObserver` sustituye el emoji inicial de botones, encabezados, etiquetas y apartados por el icono de línea equivalente (`_EMO` → `ICO`).
- Excluye el contenido del usuario: notas, marcas que elige, campos editables, `select` y avisos de texto.
- Así ningún emoji vuelve a «hacer de icono», aunque una vista nueva lo use.
- El botón «i» de ayuda deja la «i» en Georgia (tercera tipografía) y pasa a un icono de línea por máscara CSS.

### Sistema
- **Escala de radios:** 4 · 8 · 12 · 16 · 20 · pastilla (999) · círculo. Antes había 19 valores distintos.
- **Atajo de la paleta según plataforma:** «⌘K» en Mac y «Ctrl K» en el resto.
- **Verde «bien» en oscuro:** `#3bb273`, menos saturado y acorde con la paleta cálida.
- **Paleta Ctrl+K:**
  - Sin el marco heredado de `.modal`.
  - Un icono distinto por vista.
  - El elemento seleccionado usa `--acento-fondo`, con un contraste ≥ 5:1 frente al blanco.

### Composición
- **Distribución como libro de cuentas:**
  - Las 17 tarjetas idénticas con borde de color pasan a filas: nombre y peso, minigráfica, importe.
  - Una línea de peso en la base de cada fila (`scaleX(--peso)`).
  - Dos columnas en escritorio.
  - El anillo comparte fila con su leyenda desde 900 px.
- **Cifras de Inmuebles alineadas:** con subgrid, la etiqueta, la cifra y la nota comparten filas entre tarjetas, aunque una etiqueta ocupe dos líneas.
- **Sub-pestañas del Panel en móvil y tableta:** el carril deslizable escondía «Ingresos» e «Inmuebles», así que pasan a chips en flujo con todas visibles. La activa va en tinta sólida.
- **Navegación de Ingresos (tercer nivel):** píldoras, distintas del subrayado (primer nivel) y de los chips o segmentos (segundo nivel).
- **Filtros y periodo en móvil:**
  - Filtros en una rejilla de dos columnas con la etiqueta encima del valor.
  - Accesos rápidos del periodo a todo el ancho.
  - Rango de fechas en una sola fila.
  - Antes se partían al azar.
- **Rentabilidad en móvil:**
  - Ventanas en 2 columnas.
  - Las tablas desplazables muestran una sombra en el borde con más contenido (fondos `local/scroll`, sin JS).
- **Ayuda:** columna de lectura centrada de 920 px en pantallas anchas.
- **Barra superior móvil:** objetivos táctiles de 40 px.

### Primera pintura: por qué se mantiene la ocultación hasta pintar
- El árbitro 1 pidió quitar el `visibility:hidden` previo a la primera pintura de datos.
- Lo mantengo por cuatro razones:
  - Sin él vuelve el CLS de 0,97: el contenido salta al llegar los datos y el banner.
  - El elemento LCP es el texto del diálogo de bienvenida, que está **fuera** de `.env`; lo comprobé en Lighthouse, tanto en la base como en la rama.
  - El LCP móvil de la rama (≈ 9,9 s) es igual al de la base (≈ 9,1–9,9 s, mismo elemento).
  - El rendimiento sube de 30 a ~58 en móvil y de 61 a ~90 en escritorio.
- Para que nunca quede en blanco:
  - `<noscript>` lo muestra sin JS.
  - Una red de seguridad lo muestra a los 2 s aunque falle el script.
  - Se quitó el preload de Fraunces para no competir con la fuente de texto.
