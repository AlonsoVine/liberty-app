<p align="center">
  <img src="app/web/icono-512.png" alt="Liberty" width="120">
</p>

<h1 align="center">Liberty</h1>

<h3 align="center">Tu patrimonio de hogar en un panel claro, bonito y 100 % privado, que funciona en tu propio ordenador.</h3>

<p align="center">
  <a href="https://alonsovine.github.io/liberty/"><b>⬇️ Descargar</b></a> ·
  <a href="https://github.com/AlonsoVine/liberty/releases/latest"><b>Últimas versiones</b></a>
</p>

Inversiones (fondos, ETF, acciones, cripto, oro, planes de pensiones, bonos…), cuentas del banco, un piso, tus deudas, tus ingresos y gastos del día a día. Lo metes una vez y **Liberty** descarga los precios solo, calcula lo que has ganado, tu rentabilidad real (**TIR** y **TWR**), y te enseña tu patrimonio neto y su evolución en un panel pensado para entenderlo de un vistazo. **Nada sale de tu ordenador.**

> **Aviso.** Es una herramienta informativa. **No es asesoramiento financiero** ni una recomendación de compra o venta. Los precios vienen de servicios públicos gratuitos y pueden tener errores o retrasos: no se garantiza la exactitud de los datos.

---

## Índice

- [Qué hace](#qué-hace)
- [Descargar e instalar](#descargar-e-instalar)
- [Primer uso](#primer-uso)
- [Meter tus datos](#meter-tus-datos)
- [Importar de golpe (CSV, Excel o con una IA)](#importar-de-golpe)
- [El día a día](#el-día-a-día)
- [Rentabilidad y comparación](#rentabilidad-y-comparación)
- [Mucho más que inversiones](#mucho-más-que-inversiones)
- [Copias de seguridad y cambiar de ordenador](#copias-de-seguridad-y-cambiar-de-ordenador)
- [Publicar tu panel como web](#publicar-tu-panel-como-web)
- [Actualizar a una versión nueva](#actualizar-a-una-versión-nueva)
- [Privacidad](#privacidad)
- [Limitaciones conocidas](#limitaciones-conocidas)
- [Para desarrolladores: cómo está hecho](#para-desarrolladores-cómo-está-hecho)
- [Licencia](#licencia)

---

## Qué hace

- **Todo tu patrimonio en un sitio**: inversiones, cuentas, inmuebles, planes de pensiones, deudas, reservados (huchas con objetivo) e ingresos y gastos del hogar.
- **Precios automáticos** de Morningstar, Yahoo Finance y CoinGecko, con conversión a euros.
- **Buscador por ISIN, ticker o nombre** que comprueba que el producto tiene precio antes de guardarlo y rellena solo la comisión (TER), el riesgo y la categoría.
- **Cifras honestas**: aportado, plusvalía, **TIR** (money-weighted) y **TWR** (time-weighted) por producto y del total, rentabilidad por año, peor caída, racha de aportaciones…
- **Comparación**: con tus mismas aportaciones, ¿cuánto tendrías hoy en el MSCI World, el S&P 500, una cartera 60/40 o en Bitcoin?
- **Ingresos y gastos** con categorías, presupuestos, tasa de ahorro, cascada, tendencias y mapa de calor de estacionalidad.
- **Organización del hogar**: titulares, multidivisa, dimensiones de clasificación propias, avisos automáticos configurables, agenda y recordatorios.
- **Notas, biblioteca de documentos y facturas adjuntas**, todo guardado en tu ordenador.
- **Importación** desde el CSV de MyInvestor, una plantilla de Excel o el extracto de cualquier banco convertido con una IA gratuita.
- **Copias de seguridad** automáticas y en `.zip` (con tus facturas), exportación del panel a una página web (con opción de **ocultar importes**), tema claro u oscuro y modo vídeo a pantalla completa.

---

## Descargar e instalar

Liberty se descarga como **un único programa**, listo para usar. No hay que instalar nada más ni saber programar.

👉 **Página de descargas: [alonsovine.github.io/liberty](https://alonsovine.github.io/liberty/)**

### Windows

1. Descarga **`Liberty.exe`** desde la [página de descargas](https://alonsovine.github.io/liberty/).
2. Haz **doble clic**. La primera vez Windows puede mostrar un aviso azul («Windows protegió su PC»): es normal con cualquier programa descargado que no viene de una tienda. Pulsa **«Más información» → «Ejecutar de todas formas»**.
3. Liberty se abre **en tu navegador**. Deja la ventana del programa abierta mientras lo uses.

### Mac

1. Descarga el **`.dmg`** que corresponda a tu Mac desde la [página de descargas](https://alonsovine.github.io/liberty/):
   - **Apple Silicon** (M1, M2, M3, M4) — ya disponible.
   - **Intel** (Macs anteriores a 2020) — próximamente.

   ¿Cuál tienes? Menú  → **«Acerca de este Mac»**: si pone «Chip M…», Apple Silicon.
2. Abre el `.dmg` (doble clic) y **arrastra Liberty a la carpeta Aplicaciones**.
3. La primera vez, como no está firmada con un certificado de pago de Apple, ábrela con **clic derecho sobre Liberty → «Abrir» → «Abrir»** (o desde **Ajustes del Sistema → Privacidad y seguridad → «Abrir de todos modos»**). Después, doble clic normal.

> ¿Te preocupa el aviso de seguridad? Liberty es **100 % local**: no manda tus datos a ningún sitio. Puedes verificar el `Liberty.exe` descargado comparando su SHA-256 con el publicado en cada [versión](https://github.com/AlonsoVine/liberty/releases/latest).

---

## Primer uso

La primera vez verás una **cartera de ejemplo**, para curiosear todo sin miedo.

Cuando quieras usar la tuya, pulsa **«Empezar con mis datos»** y elige:

- **Empezar de cero**: una cartera vacía.
- **Copiar el ejemplo para practicar**: puedes tocar y borrar lo que quieras.

Si más adelante quieres volver a empezar, en **Mis datos** tienes **«Empezar de nuevo…»**. Tu cartera anterior se guarda antes en las copias, por si acaso. Hay además un **tour guiado** que te enseña toda la app paso a paso.

---

## Meter tus datos

Todo está en la pestaña **Mis datos**.

### Añadir un producto

1. **Activos → «+ Añadir producto»**.
2. En el buscador, escribe el **ISIN** (como `IE00BYX5NX33`), el **ticker** (`AAPL`, `SAN.MC`) o el **nombre** (`bitcoin`, `oro`).
3. Pulsa el resultado. Se rellenan solos el nombre, el tipo, la fuente del precio, la moneda y, en fondos y ETF, la comisión (TER), el riesgo y la categoría.
4. **Guardar producto**. Justo después se abre el formulario de **su primera compra**.

¿No cotiza en internet (un plan de pensiones, un depósito, oro físico, un piso)? Créalo igual y elige **«Valor anotado a mano»** como fuente del precio.

### Movimientos: compras, ventas, dividendos y comisiones

**Saldos y movimientos → «+ Añadir movimiento»**. Para cada operación:

- **Unidades**: participaciones, acciones, onzas…
- **Importe total en euros**: en una compra, lo que salió de tu cuenta **con las comisiones incluidas**; en una venta o un dividendo, lo que te ingresaron.
- **Comisión** (opcional): solo informativa, ya va dentro del importe.

Las ventas descuentan el coste por **FIFO** (primero lo más antiguo), como hace Hacienda.

### Cuentas, planes de pensiones, pisos… (valores anotados a mano)

1. Crea el producto (para una cuenta, el tipo **«Cuenta / efectivo»**; para lo demás, la fuente **«Valor anotado a mano»**).
2. En **Saldos y movimientos**, anota su valor con la fecha. Si sabes lo aportado (p. ej. a un plan de pensiones), anótalo y el panel calculará su rentabilidad.
3. Una vez al mes basta: con **«Anotar todos de una vez»** copias todos los saldos de tu banco en un minuto.

### Ingresos y gastos del hogar

En **Mis datos → Ingresos y gastos** anotas nóminas, alquileres, recibos… por categoría (o los importas del banco). En **Panel → Ingresos y gastos** los ves resumidos: ahorro y tasa de ahorro, en qué se va el dinero, tendencias y presupuesto.

---

## Importar de golpe

**Mis datos → Importar**. Hay tres caminos y **siempre verás una vista previa antes de guardar nada**, con los totales para compararlos con tu banco y los errores explicados fila por fila.

### MyInvestor (fondos)

1. En MyInvestor, abre **cada fondo → «Plusvalías y minusvalías»** → descarga el **CSV**. No le cambies el nombre: lleva el ISIN.
2. Arrastra todos los CSV a la vez y pulsa **«Revisar antes de importar»**.

Cada importación **sustituye** lo anterior de ese fondo, así que puedes repetirlo cada mes sin duplicar nada. Para **ETF o acciones** (que MyInvestor no deja exportar), usa capturas y la opción **«Con ayuda de una IA»**.

### Plantilla de Excel o CSV (cualquier banco)

Descarga la plantilla desde la app (**Excel** o **CSV**). Trae desplegables, una hoja **«Ejemplo»** y una de **«Instrucciones»**. Rellena **«Movimientos»**, una fila por operación:

| Columna | ¿Obligatoria? | Qué poner |
|---|---|---|
| `fecha` | Sí | `10/03/2025` o `2025-03-10`. |
| `identificador` | Casi siempre | ISIN o ticker. Vacío solo en cuentas y cosas sin precio. |
| `nombre` | Si no hay identificador | Nombre del producto o de la cuenta. |
| `tipo_producto` | No | `fondo`, `etf`, `accion`, `cripto`, `commodity`, `bono`, `pension`, `efectivo`, `inmueble`, `deuda` u `otro`. |
| `tipo_movimiento` | Sí | `compra`, `venta`, `dividendo`, `comision` o `saldo`. |
| `unidades` | Recomendado | Si lo dejas vacío, se calculan con el precio de ese día. |
| `importe` | Sí | Dinero total. Compra: lo que salió, con comisiones. Venta/dividendo: lo que entró. |
| `moneda` | No | Si no es EUR, se convierte con el cambio de ese día. |
| `comision` | No | Ya incluida en el importe. |
| `nota` | No | Lo que quieras. |

### Con ayuda de una IA (cualquier extracto)

Una IA gratuita (ChatGPT, Gemini, Copilot…) puede convertir el extracto de tu banco, un PDF o **capturas** de tus órdenes a la plantilla.

> ⚠️ **Antes de dárselo a la IA, borra (o tapa en las capturas) tu nombre, DNI, IBAN, números de cuenta y tarjeta, dirección y cualquier dato personal.** Solo hacen falta fechas, productos e importes.

1. En la app, pulsa **«Copiar prompt»** (o cópialo de aquí abajo).
2. Pégalo en la IA y, debajo, tu extracto (o adjunta el PDF o las capturas).
3. Copia la respuesta, pégala en la app y pulsa **«Revisar antes de importar»**.
4. **Compara los totales de la vista previa con tu banco**: una IA puede equivocarse al copiar un número o saltarse una fila.

<details>
<summary><b>Ver el prompt para la IA</b></summary>

```text
Convierte el extracto de mi banco o bróker (el texto que pego al final, o los PDF o capturas de pantalla que adjunto) en una tabla para importarla en mi app de patrimonio. En las capturas de órdenes, lee con cuidado la fecha de ejecución, los títulos, el precio y el importe de cada una.

Devuélveme SOLO un CSV dentro de un bloque de código, sin explicaciones, separado por punto y coma (;) y con esta cabecera exacta:
fecha;identificador;nombre;tipo_producto;tipo_movimiento;unidades;importe;moneda;comision;nota

Reglas para cada columna:
- fecha: la fecha de la operación (o de ejecución), en formato AAAA-MM-DD.
- identificador: el ISIN si aparece (12 caracteres, como IE00BYX5NX33); si no, el ticker (como AAPL). Para cuentas bancarias, déjalo vacío.
- nombre: el nombre del producto o de la cuenta, tal y como aparece.
- tipo_producto: una de estas palabras: fondo, etf, accion, cripto, commodity, bono, pension, efectivo, inmueble, deuda, otro.
- tipo_movimiento: una de estas palabras: compra, venta, dividendo, comision, saldo. Usa «saldo» solo para el saldo de una cuenta en una fecha.
- unidades: participaciones, acciones o unidades compradas o vendidas, en positivo y con punto decimal. Déjalo vacío si no aparece.
- importe: el dinero total de la operación, en positivo, con punto decimal y sin símbolo de moneda. En una compra, lo que salió de la cuenta con las comisiones incluidas; en una venta o un dividendo, lo que entró.
- moneda: la moneda del importe (EUR, USD…).
- comision: la comisión de esa operación si aparece (ya va incluida en el importe). Si no, vacío.
- nota: vacío, o una nota muy breve.

Importante:
- Una fila por operación, ordenadas por fecha.
- No inventes nada: si un dato no aparece en el extracto, deja esa casilla vacía.
- No incluyas nóminas, recibos, gastos del día a día ni transferencias entre mis propias cuentas.

EXTRACTO:
[Pega aquí tu extracto o adjunta los PDF o capturas. ANTES, BORRA o tapa tu nombre, DNI, IBAN, números de cuenta y tarjeta, dirección y cualquier dato personal: solo hacen falta fechas, productos e importes.]
```

</details>

---

## El día a día

- **Actualizar precios**: la app los actualiza sola al abrirse y con el botón **«↻ Actualizar precios»**. En la ficha de cada producto verás de dónde sale su precio y de qué día es.
- **Tu rutina mensual**: importa los CSV, anota tus compras de bolsa y pulsa **«Anotar todos de una vez»** con los saldos de tus cuentas. Cinco minutos.
- **Solo largo plazo**: un botón quita lo que no es inversión (tu colchón, las cuentas…) y recalcula todas las cifras.
- **Modo vídeo** (tecla `V`): pantalla completa para grabar o presentar tu panel. Las teclas `1`…`7` cambian de pestaña.
- **Tema claro u oscuro** con el botón **«Tema»**.

---

## Rentabilidad y comparación

En **Panel → Rentabilidad** tienes una tabla central con la **TIR** y la **TWR** de cada producto y del total, en distintos marcos (total, por año, por mes). Y en la comparación **«¿Y si lo hubiera metido en otro sitio?»**, Liberty repite **tus mismas compras y ventas, en las mismas fechas**, pero en otra cartera, y te dice cuánto tendrías hoy:

- **MSCI World** (ETF iShares IWDA, en euros)
- **S&P 500** (ETF iShares SXR8)
- **Cartera 60/40** (60 % MSCI World + 40 % bonos globales cubiertos, EUNA)
- **Sin riesgo** (un monetario del euro, XEON)
- **Bitcoin**

Con la volatilidad, el Sharpe y la peor caída de cada una en «Ver más detalles».

---

## Mucho más que inversiones

- **Deudas y vencimientos**: hipoteca, préstamos, tarjetas; ratios deuda/activos y cuota/ingresos, y los próximos vencimientos.
- **Reservados**: huchas con objetivo (el viaje, el coche, el colchón) con su color y progreso.
- **Informe fiscal**: plusvalías/minusvalías realizadas, dividendos y cupones por año natural (FIFO).
- **Notas, tablero y agenda**: notas con etiquetas y checklists, un tablero tipo Trello y una agenda/calendario que junta tus recordatorios con los vencimientos.
- **Biblioteca de documentos** y **facturas adjuntas** a cada apunte, todo guardado en tu ordenador.
- **Avisos automáticos** configurables (concentración, colchón, vencimientos cercanos, «hace X días que no anotas»…).

---

## Copias de seguridad y cambiar de ordenador

En **Mis datos → Copias**:

- **Copias automáticas**: antes de cada cambio se guarda una copia (las últimas 20). Si te equivocas, pulsa **«Recuperar»** en la de antes del error.
- **Descargar copia**: un **`.json`** con toda tu cartera, o un **`.zip`** que incluye además tus **facturas** y tu **biblioteca**. Guárdalo en tu nube o en un USB de vez en cuando.
- **Recuperar desde un archivo**: para pasar tu cartera a otro ordenador. En el nuevo, instala Liberty, ábrelo y sube ahí el archivo. Al restaurar, tus facturas actuales se respaldan primero: **nunca se pierde nada**.

---

## Publicar tu panel como web

En **Mis datos → Copias** puedes descargar tu panel en **un solo archivo HTML**, de solo lectura. Ábrelo con doble clic, mándalo por correo o súbelo a internet (por ejemplo, arrastrándolo a [app.netlify.com/drop](https://app.netlify.com/drop)).

Con la opción **«Ocultar importes»**, las cantidades en euros **no van dentro del archivo** (ni escondidas en el código): solo se ven los porcentajes y la forma de las gráficas.

---

## Actualizar a una versión nueva

Cuando haya una versión nueva, Liberty te avisa con un mensaje arriba. Como tus datos viven aparte de la aplicación, actualizar **no borra nada**: descarga el nuevo `Liberty.exe` (o el `.dmg`) desde la [página de descargas](https://alonsovine.github.io/liberty/) y ábrelo. En Windows, el botón de aviso puede incluso descargártelo y dejarlo junto al actual.

---

## Privacidad

- Tus datos se guardan **solo en tu ordenador**. No hay cuentas, ni servidores, ni nadie más que los vea.
- Liberty solo sale a internet para **descargar precios** (Morningstar, Yahoo Finance, CoinGecko) y para **comprobar si hay una versión nueva** en GitHub. En esas consultas no va ningún dato tuyo.
- El servidor de la app solo escucha en tu propio ordenador (`127.0.0.1`): nadie de tu red puede entrar.

---

## Limitaciones conocidas

- Los precios vienen de servicios **gratuitos y no oficiales**. Casi siempre van bien, pero pueden fallar o traer algún dato raro. Si una fuente no responde, Liberty usa el último precio guardado y te avisa.
- Del CSV de MyInvestor solo se conoce la **plusvalía** de lo ya vendido, no la fecha de venta: tu patrimonio de hoy sale bien, pero la curva no refleja cuándo vendiste.
- El cálculo fiscal es **orientativo** (FIFO por año natural); no sustituye a tu declaración.
- La versión de **Mac para Intel** está en camino; por ahora el `.dmg` disponible es para Apple Silicon.

---

## Para desarrolladores: cómo está hecho

- **Python + Flask** para el servidor local; el panel es HTML, CSS y JavaScript **sin librerías externas** (gráficos SVG propios). Sin Node en tiempo de ejecución.
- Los datos están en `mis_datos/` (una carpeta por cartera): productos, movimientos, valores anotados, flujos, notas, adjuntos…
- Se empaqueta con **PyInstaller** en `Liberty.exe` (Windows) y en `Liberty.app` → `.dmg` (macOS, vía GitHub Actions).

```
app/
  servidor.py    la app local (Flask, solo en 127.0.0.1)
  motor.py       los cálculos: series diarias, TIR/XIRR, TWR, comparación, avisos
  buscar.py      buscador de productos (Morningstar, Yahoo, CoinGecko)
  importar.py    importadores (MyInvestor, plantilla, texto de la IA)
  almacen.py     validación y guardado, con copias automáticas
  exportar.py    el panel como web estática
  web/           el panel (index.html, app.js, graficos.js, editor.js)
  demo/          la cartera de ejemplo
mis_datos/       TUS DATOS (se crea al usarla; no se sube a ningún sitio)
tests/           pytest (backend) · tests-js/ jsdom (frontend)
```

Arrancar desde el código:

```bash
uv run python -m app      # o:  python -m app
```

Tests: `pytest -q` y `npm test`.

---

## Licencia

Liberty es **software propietario**: todos los derechos reservados. Puedes **descargarlo y usarlo para tu uso personal**, pero no copiarlo, modificarlo, redistribuirlo ni usarlo con fines comerciales sin permiso escrito del autor. Consulta el archivo **[LICENSE](LICENSE)** para los términos completos (incluye el aviso de la obra original de la que deriva).

© 2026 Alonso ([github.com/AlonsoVine](https://github.com/AlonsoVine)).

**Herramienta informativa. No es asesoramiento financiero ni una recomendación de inversión. No se garantiza la exactitud de los datos ni de los precios. Úsala bajo tu propia responsabilidad.**
