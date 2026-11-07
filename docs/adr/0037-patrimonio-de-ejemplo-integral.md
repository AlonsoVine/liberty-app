# ADR 0037 — Patrimonio de ejemplo integral, con fechas vivas

- **Estado:** aceptado (pendiente de publicar)
- **Fecha:** 2026-11-03

## Contexto

El patrimonio de ejemplo es un único origen y se usa en tres sitios:

- la demo de la primera vez, en solo lectura;
- «Empezar con mis datos → copia del ejemplo»;
- Ayuda → «🧪 Crear un patrimonio de ejemplo».

Era un JSON fijo (`demo/cartera.json`) que se había quedado atrás:

- estaba desequilibrado: unos 58.000 € de cartera frente a 261.000 € de inmuebles;
- tenía apuntes de solo dos meses, con fechas fijas. Cada mes era más viejo y recibía con avisos que parecían errores («hace 33 días que no anotas», «alquiler sin cobrar»);
- los activos a mano no tenían «aportado», así que su rentabilidad salía «n/d» y la TIR total daba un 41 %;
- ningún activo estaba en negativo;
- el trastero y el garaje seguían dentro de la cartera;
- no había notas, cuadernos, agenda, tablero, biblioteca ni facturas.

Alonso pidió un ejemplo que cubra toda la app y esté equilibrado entre cartera e inmuebles. Eligió:

- **fechas vivas**;
- **unos 300.000 €**, repartidos en unos 150.000 € de cartera y 150.000 € de inmuebles netos;
- titulares **«Yo», «Mi pareja» y «Común»**.

## Decisiones

- **Generador en lugar de JSON** (`app/ejemplo.py`).
  - `genera(hoy, precios)` devuelve `(cartera, con_precios_reales)`.
  - Las fechas son relativas a hoy: 36 meses de historia más el mes en curso, hasta el día de hoy.
  - Es determinista: el mismo día da el mismo ejemplo, y un mes ya pasado sale igual día tras día (azar sembrado por mes).
  - `demo/cartera.json` desaparece del repo, del `.exe`, del `.dmg` y de la imagen Docker.
- **Precios reales para lo que cotiza.** Las unidades de cada compra se calculan con el precio de ese día:
  - se toma el último conocido en un margen de 120 días, como el relleno del motor;
  - el precio sale de la caché de la demo, mediante `motor.precios_en_cache`, que no sale a la red;
  - si no hay caché, se usa un precio aproximado;
  - el servidor lo rehace con los precios reales en cuanto el motor los baja (`recalcula`), y antes de copiarlo (`ejemplo_con_precios`).
- **Servidor:**
  - `cartera_ejemplo()` lo genera una vez al día por carpeta y lo guarda en memoria;
  - `datos.js` recalcula la demo si su cálculo es de otro día;
  - las copias se llevan los documentos y la caché de precios (`copia_documentos_ejemplo`).
- **Documentos de muestra:**
  - son PDF mínimos y válidos de una página con texto («Documento de muestra… no es real»), no archivos vacíos, porque un archivo vacío falla al abrirlo;
  - se escriben en `adjuntos/` y `biblioteca/` de la demo y de cada copia;
  - nunca pisan lo que ya hay.
- **El hogar.** Una pareja con:
  - su casa, con una hipoteca que no está enlazada a ninguna deuda;
  - un piso alquilado en Valencia, con su hipoteca enlazada a una deuda, el inquilino anterior con su contrato terminado y la inquilina actual con contrato IRAV;
  - una plaza de garaje alquilada;
  - un trastero en venta.

  Su cartera tiene:
  - fondos y un ETF indexados, un fondo monetario, bitcoin y Apple en dólares;
  - un plan de pensiones, un PIAS, oro, Letras del Tesoro, una acción en pérdidas y crowdfunding en pérdidas, con un tipo propio;
  - cuatro cuentas, una de ellas en USD;
  - un préstamo de coche y una tarjeta.

  Fiscal tiene contenido en el último año cerrado: ventas con ganancia y con pérdida, dividendos con retención y comisiones.
- **Avisos a propósito, y solo esos:**
  - el vencimiento cercano de las Letras;
  - una fecha de la agenda (la ITV);
  - la revisión anual de la renta (IRAV);
  - el cobro próximo del alquiler;
  - una alerta de precio cumplida (el crowdfunding).

  Nunca salen los que delatarían un ejemplo viejo: sin anotar, sin actualizar, alquiler sin cobrar, valor antiguo, dinero libre negativo, concentración, etc.
- **Ingresos y gastos:**
  - unos 1.000 apuntes con estacionalidad (pagas extra, IBI, vacaciones, Navidad);
  - presupuestos y plantillas recurrentes;
  - reglas del banco y marcas;
  - la dimensión «Naturaleza» (Fijo, Variable o Extraordinario);
  - observaciones y 10 facturas;
  - el año más antiguo archivado.
- **Documentos:**
  - 13 notas, en 3 cuadernos y sueltas, enlazadas a activos, deudas, reservados, inmuebles, archivos y carpetas, con listas de tareas, colores y notas fijadas;
  - 8 recordatorios (que no se repiten, mensuales y anuales, con uno ya hecho);
  - un tablero de 3 columnas;
  - una biblioteca con carpetas anidadas, 14 documentos y uno en la papelera;
  - documentos enlazados a contratos.

## Retrocompatibilidad

Las carteras ya creadas desde el ejemplo son copias fijas y no se tocan. La demo y las copias nuevas usan el ejemplo nuevo.

## Tests

`tests/test_ejemplo.py` sustituye a `test_demo_dataset.py` (+12 tests en total; pytest 359). Comprueba:

- **la cobertura:** cada colección, cada tipo de activo, cada fuente y cada tipo de movimiento, las dos monedas, los usos, estados y contratos de los inmuebles, y que todos los enlaces existen;
- **la forma:** que notas, cuadernos, agenda y tablero son idénticos a lo que guarda `almacen`;
- **los PDF:** que son válidos y que no se pisan;
- **siete días con trampa** (fin de mes, febrero, Año Nuevo, agosto…), con `motor.hoy` fijado:
  - el mes en curso tiene apuntes y no hay fechas futuras;
  - salen los avisos elegidos y ninguno falso;
  - la libertad financiera se calcula con 12 meses;
- **el determinismo** y que las compras van al precio real;
- **Fiscal** del último año cerrado;
- **el equilibrio:** cartera e inmuebles entre 120.000 y 190.000 €, ningún activo por encima del 50 % y entre 1 y 3 activos en negativo;
- **el servidor:** que la demo y la copia sirven sus facturas y documentos.
