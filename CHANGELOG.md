# Registro de cambios

**Liberty** — gestor de patrimonio de hogar 100 % local (superconjunto del Excel
`Gestor_Patrimonial`). Deriva de **Rumbo** (MIT, de Dani Dominguez Quant); la atribución
a la obra original se mantiene en [LICENSE](LICENSE) y en el «Acerca de» de la app. Las
versiones se publican en [AlonsoVine/liberty](https://github.com/AlonsoVine/liberty)
(`Liberty.exe` para Windows y `Liberty-macOS.dmg` universal para Mac). Ver también
[docs/ROADMAP.md](docs/ROADMAP.md) y los ADR en [docs/adr/](docs/adr/).

Todos los cambios son **aditivos**: una cartera anterior sigue funcionando igual.

## [No publicado] — próxima v1.16.0

- **Liberty en Docker (nueva forma de ejecutarlo).** Además del `.exe` y el `.dmg`, ahora se
  publica una **imagen Docker multiarquitectura** (`ghcr.io/alonsovine/liberty`, `amd64` y
  `arm64`) para tener una **sola instancia en casa** —p. ej. en una Raspberry Pi— a la que
  acceder desde varios dispositivos por una red privada (VPN/Tailscale). Es el **mismo
  código** que el escritorio; lo que cambia entre vías (carpeta de datos, host, puerto, modo)
  se centraliza en `app/entorno.py`. En el contenedor sirve con **waitress** y cierra limpio
  ante `docker stop`. Guía y `docker-compose.yml` de ejemplo (endurecido) en el README.
- **Más seguridad de acceso.** El servidor acepta, además de `localhost`, los nombres de
  equipo que indiques (`LIBERTY_HOSTS_PERMITIDOS`, coincidencia exacta) para funcionar tras
  Tailscale o un proxy, y rechaza peticiones con `Origin`/`Referer` ajeno (defensa CSRF).
- **Acceso desde varios dispositivos sin pisarse.** Si alguien cambia de cartera en otro
  dispositivo mientras tú editas, Liberty no escribe en la cartera equivocada: avisa y te
  pide recargar.
- **La carpeta de datos, visible en Ajustes** (solo lectura). En Docker, el aviso de versión
  nueva explica cómo actualizar la imagen en vez de descargar un binario.
- **Avisos del panel en una caja discreta y plegable.** Los avisos se agrupan bajo una
  cabecera slim («🔔 N avisos»); al plegarla ocupa una sola línea y el estado se recuerda
  y se mantiene al cambiar de pestaña, para no hacer scroll en cada vista. Si aparece un
  aviso nuevo que no habías visto, la cabecera lo marca con «nuevo» aunque esté plegada;
  al abrirla, los avisos quedan como vistos y el indicador desaparece.

## [1.15.0] — 2026-10-25

Madurez de UX e identidad propia. ADR 0024 y 0025.

- **Control de periodo en Ingresos y gastos**: selector «Periodo» (Este mes · Año · 12
  meses · Rango desde→hasta) que recalcula el Resumen y las Categorías al tramo elegido,
  respetando los filtros del panel.
- **Tooltip «Total» de la evolución enriquecido**: al pasar el ratón muestra aportado,
  plusvalía, rentabilidad % y la línea de inflación de ese día (antes solo el aportado).
- **Icono de calendario visible en modo oscuro** en los campos de fecha.
- **Pestañas del panel agrupadas por tema** (segmentado, como Mis datos): Inicio ·
  (Patrimonio · Distribución · Rentabilidad · Evolución · Deudas · Fiscal) · Ingresos y
  gastos. «Mis datos» reagrupado en coherencia.
- **Filtros de Ingresos y gastos más limpios**: el «Filtrar apuntes» va en la misma línea
  que el periodo, y se ocultan los filtros de clase de activo y geografía (no aplican a
  apuntes de caja); queda solo el titular.
- **Interruptor de atajos de teclado** en Ajustes (para quien los pulsa sin querer);
  Escape y la paleta Ctrl/⌘+K siguen funcionando siempre.
- **Identidad propia**: README reescrito con marca Liberty (sin referencias a Rumbo) y
  **licencia híbrida** (aviso MIT de la obra original intacto + derechos reservados sobre
  las aportaciones de Liberty, con uso personal permitido).
- **Mac: un único `.dmg` universal2** (Apple Silicon + Intel en el mismo binario).

## [1.14.1] — 2026-10-23

ADR 0023.

- **Comparación de Rentabilidad** «¿Y si lo hubiera metido en otro sitio?»: añadido
  **Bitcoin** como referencia, junto a MSCI World, S&P 500, 60/40 y monetario.
- **Iconos «i»** en las cabeceras TIR y TWR de la tabla central, explicando
  money-weighted vs. time-weighted.
- **CSV de Ingresos y gastos a medida**: importe numérico, divisa en columna propia,
  observaciones y facturas con contenido real; respeta filtro, búsqueda y orden.

## [1.14.0] — 2026-10-21

ADR 0020, 0021 y 0022.

- **Tabla central de Rentabilidad** (Total / Año / Mes): resumen y detalle por activo con
  TIR y TWR; filas pulsables que llevan a la ficha del producto.
- **Avisos de agenda configurables** (días de antelación) con navegación directa al día
  en la agenda, y **avisos homogéneos** (mismo aspecto e icono de sección) en el Panel y
  en Mis datos.
- **Ingresos y gastos**: borrado sin perder el scroll, selección múltiple opcional,
  archivar/desarchivar/borrar por fecha, y opción de que los archivados cuenten o no en el
  panel.
- **4 pestañas de Configuración en una línea** y ayuda «i» al día.

## [1.13.0] — 2026-10-20

ADR 0019.

- **Cuadernos de notas**: agrupar notas en cuadernos propios (crear, renombrar, borrar,
  mover).
- **Nota a pantalla completa**: la tarjeta recorta el texto largo y al pulsarla se abre un
  modal grande con checklist operativo y acciones.
- **Agenda**: iconos de editar/borrar en la lista y hover propio del recordatorio en el
  calendario.
- **Visibilidad de documentos configurable** y nueva pestaña «Documentos» en
  Configuración (con la papelera de archivos).

## [1.12.0] — 2026-10-20

ADR 0018.

- **Notas documentales**: una nota puede enlazar varios activos y varios documentos, con
  color y pin; chips navegables al activo o a la carpeta.
- **Agenda navegable**: los vencimientos y las tarjetas del tablero llevan a su ficha con
  la fila resaltada.
- **Filtro «— Sin categoría —»** en Ingresos y gastos.
- **Tablas con cabeceras fijas + scroll** y un pie discreto con el número de registros.

## [1.11.2] — 2026-10-19

- **Ayuda contextual reescrita**: cards concretas y con ejemplos (dimensiones, reglas del
  banco, titular por defecto, rebalanceo, FIFO…) e iconos «i» homogéneos con popover que
  se muestra al pasar el ratón y al pulsar.
- Primera versión con **Liberty.app para Mac** (Apple Silicon, sin firmar).

## [1.11.1] — 2026-10-19

- **Saltos con filtro desde los gráficos**: el donut de Distribución lleva a Saldos y
  movimientos del producto/grupo; el donut de categorías de Ingresos, a los flujos
  filtrados por categoría y tipo.
- **Barra de filtros potenciada en Movimientos** (producto, operación, entidad,
  dimensiones, importe, fechas); botón **«Anotar saldo»** en las fichas a mano; arreglo
  del tooltip de los gráficos.

## [1.11.0] — 2026-10-18 · Base del gestor de patrimonio

Primera versión publicada del gestor (sobre la app original Rumbo). Reúne los cimientos
F0–F5, las baterías A · B · C y el rediseño de navegación, más una batería visual y la
ayuda contextual. ADR 0001–0007 y siguientes.

### Correcciones y batería visual de esta versión
- Correcciones del análisis: carrera de datos del motor, doble escapado en Inicio,
  valoraciones con fecha futura ignoradas, export «ocultar importes» y huérfanos al subir
  carpetas.
- **Batería UI/UX**: tokens de movimiento y `prefers-reduced-motion`, hover/press y foco
  visible, animaciones de entrada de los gráficos, count-up del héroe, barra de carga,
  faro en las barras de objetivo, toast rediseñado y crossfades al cambiar de vista.
- **Ayuda contextual**: botón «i» integrado al final de la barra de navegación de cada
  zona, que abre un modal con la explicación de la pantalla actual; interruptor en Ajustes.

### Baterías de mejoras A · B · C
- **A1** Presupuestos por categoría (real vs. presupuesto, margen) · **A3** gráficas de
  evolución del hogar (patrimonio neto y deudas; ingresos/gastos/ahorro).
- **B1** Rebalanceo (cuánto aportar/reducir por tipo) · **B2** filtro por titular en el
  Panel · **B3** recordatorio «hace N días que no anotas» (configurable) · **B4** cierre
  del mes.
- **C1** Tests de frontend con jsdom (y en el CI) · **C2** exportar tablas a CSV ·
  **C3** asistente de primer uso (ocultable) · **C4** accesibilidad (texto grande, atajos,
  móvil) · **C5** iconos ⓘ de ayuda.

### Ajustes de UX y correcciones
- **Objetivo de patrimonio configurable** (antes fijo en 100.000 €), en Configuración.
- **Orden de tablas más visible**: columnas ordenables con ↕ y pista junto al buscador.
- **«Empezar de nuevo»** vive solo en «Copias y seguridad».
- **Ayuda ampliada** (carteras, titulares, apartados, deudas, ingresos/gastos, dinero
  libre, objetivos, concentración, vencimientos, multidivisa, orden de tablas…).
- **Repartir colores** con confirmación.
- **Evolución por año**: elegir un año y ver el cambio «en lo que va de año» por componente.

### Tablas, renombrar, restaurar y reparto %
- **Buscar, ordenar y filtrar** en las tablas de Mis datos, con el estado conservado entre
  re-renders.
- **Renombrar la cartera** activa desde Configuración.
- **Restaurar una copia** conserva el nombre de la cartera destino; las copias incluyen
  todo (apartados, deudas, ingresos y gastos, configuración y titulares).
- **Corrección del «Reparto %»** en Evolución: ahora es la composición de los activos y
  suma 100 % en todo el eje (ya no incluye las deudas).

### Varias carteras y correcciones
- **Multi-cartera**: varias carteras conmutables desde el selector superior; cada una en
  `mis_datos/carteras/<id>/`; el modo antiguo de una sola cartera se migra solo.
- **Corrección**: en Distribución, el botón del selector se marca al pulsarlo.
- **Autoría**: Alonso (github.com/AlonsoVine) como coautor en LICENSE y en el pie.

### UX · Navegación de dos niveles
- Barra superior con tres secciones grandes: **Panel**, **Mis datos** y **Ayuda**.
- **Panel** con sub-pestañas (Patrimonio · Distribución · Rentabilidad · Evolución ·
  Ingresos y gastos · Deudas y vencimientos), banner de avisos arriba y una línea-guía en
  lenguaje llano por vista.
- **Mis datos** con pestañas (Activos · Deudas · Apartados · Ingresos y gastos · Saldos y
  movimientos · Configuración · Importar · Copias y seguridad).
- Nueva **Configuración** (como la hoja del Excel): titulares, categorías de
  ingresos/gastos, monedas, colchón, objetivos y umbrales.

### Cimientos del gestor (F0–F5)
- **F0** Suite de tests (pytest) del motor (números, XIRR, FIFO, series/divisas,
  validación y `construir()` de extremo a extremo), tooling (`ruff`, `pytest`), CI y
  documentación (ADR 0001–0003).
- **F1** Patrimonio de hogar: titulares, disponible/no disponible, apartados, colchón,
  dinero libre y bruto vs. neto; desglose por titular. (ADR 0002, 0003.)
- **F2** Deudas: ficha (capital, TAE, cuota, fechas), capital pendiente, intereses y
  ratios deuda/activos y cuota/ingresos. (ADR 0004.)
- **F3** Ingresos y gastos (ligero): flujo de caja por categoría, tasa de ahorro y
  agregados (mes, año, media 12 m). (ADR 0005.)
- **F4** Asignación y control: objetivos por tipo con desviación, concentración,
  vencimientos y panel de alertas. (ADR 0006.)
- **F5** Multidivisa y pulido: tipo de cambio manual por moneda para productos «a mano»,
  con alerta si falta. (ADR 0007.)
