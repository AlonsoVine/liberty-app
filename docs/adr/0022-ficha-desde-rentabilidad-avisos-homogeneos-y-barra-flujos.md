# ADR 0022 — Ficha desde Rentabilidad, avisos homogéneos y barra de Ingresos y gastos

- **Estado:** aceptado
- **Fecha:** 2026-10-21
- **Fase:** madurez de UX (versión 1.14.0, pulido)

## Contexto

Tres mejoras de consistencia pedidas por Alonso dentro de la 1.14.0: acceder a las fichas de
los componentes desde la tabla de Rentabilidad (como desde Distribución); que los avisos se vean
igual en el Panel y en Mis datos (hoy tenían CSS distinto) con un icono de la sección a la que
corresponden; y ordenar la barra de Ingresos y gastos para que los botones de acción no se
descoloquen al filtrar.

## Decisiones

**1. Ficha desde Rentabilidad (`app/web/app.js`).** Las filas de la tabla central de
Rentabilidad (Total/Año/Mes) son pulsables (`data-rcficha`, con un `›` de afordancia) y abren la
ficha del componente. Helper `abreFicha(id, origen)` que recuerda el origen en
`estado.fichaOrigen`; `pintaFondos` pinta el botón «Volver» según ese origen: **«← Volver a
Rentabilidad»** o «← Volver a Distribución». Todos los caminos a la ficha (cards de componentes,
donut, treemap, paleta de búsqueda) pasan por `abreFicha`. Desde la ficha, el selector superior
ya listaba **todos** los componentes, así que desde Rentabilidad se llega a la ficha de cualquiera.

**2. Avisos homogéneos (`app/web/index.html`, `app.js`, `editor.js`).** Un único estilo
`.avisoLinea` (borde redondeado, acento por nivel a la izquierda, icono de sección) para los
avisos del Panel (`#bannerAlertas` y `#avisos`) y de Mis datos (`#edAvisos`). Icono por sección
vía `window.avisoIco(a)` a partir de `pv`/`destino`: Distribución 📊, Deudas 💳, Patrimonio 💰,
Ingresos 💶, Fiscal 🧾, Agenda 🗓️, genérico ⚠️/ℹ️. El aviso de agenda se ve idéntico en los dos
sitios. **Cuidado documentado:** la clase CSS `.info` ya existe para el icono «i» (serif,
cursiva); no usarla como nivel de aviso — el nivel «info» no lleva clase (usa el borde suave por
defecto) y solo «aviso» añade `.aviso` (acento `--mal`).

**3. Barra de Ingresos y gastos en dos filas (`editor.js`, `index.html`).** `envTabla` admite un
parámetro `acciones`: cuando se define, los botones de acción (acciones propias + «☑ Seleccionar»
+ «⤓ CSV») van en una **segunda línea alineada a la derecha** (`.tablaAcciones`), debajo de los
filtros, para que estos puedan crecer (y aparezca «✕ Limpiar filtros» en su sitio) sin descolocar
nada. En Ingresos y gastos las acciones son «Ver archivados», «🗄 Archivar / borrar…»,
«Seleccionar» y «CSV»; en Movimientos, «Seleccionar» y «CSV». El resto de tablas se quedan como
estaban (una sola fila).

## Retrocompatibilidad

Aditivo y solo de presentación. `abreFicha` conserva el comportamiento por defecto
(«Distribución») para quien no venga de Rentabilidad. `envTabla` sin `acciones` se comporta como
antes.

## Tests

`ruff`, `node --check`, 14 jsdom y verificación visual por CDP: ficha abierta desde Rentabilidad
con «← Volver a Rentabilidad», avisos idénticos en Panel y Mis datos (con sus iconos de sección),
y la barra de Ingresos y gastos con las acciones a la derecha en su propia línea.
