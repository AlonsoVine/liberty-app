# ADR 0030 — Inmuebles: inquilinos, contratos, avisos, filtro y Panel sin activos

- **Estado:** aceptado (en la rama `inmuebles`; se integrará en `main` con la release que la cierre)
- **Fecha:** 2026-11-01
- **Fase:** F6 · Inmuebles — iteración 2, avisos de la 5 y pendientes de la 3 y la 4 (ver [diseño](../diseno-inmuebles.md))

## Contexto

Antes de sacar la versión, Alonso pidió cerrar cuatro cosas:

1. contratos e inquilinos;
2. avisos de los inmuebles, configurables;
3. poder ocultar los apuntes de los inmuebles en Ingresos y gastos;
4. que el Panel funcione con una cartera sin activos.

Para la 1 propuso: una sección para añadir inquilinos, con un formulario propio por contrato,
todo dentro de la ficha del inmueble, y que el usuario pueda **añadir datos con su nombre y su
valor**, mejor si un dato admite **uno o varios valores**. Para la 2: avisos de fin de
contrato, de cobro que se acerca y de un cobro que no llega, que se puedan activar, apagar y
personalizar.

## Decisiones

**A. Modelo: el inquilino manda y el contrato cuelga de él.**

```jsonc
"inquilinos": [{ "id": "q1", "nombre": "", "documento": "", "telefono": "", "email": "", "nota": "",
  "campos": [{ "nombre": "Avalista", "valores": ["Luis", "Marta"] }],
  "contratos": [{ "id": "c1", "inicio": "2025-08-01", "fin": "2030-07-31", "renta": 750,
    "diaCobro": 5, "fianza": 750, "actualizacion": "irav", "categoria": "Alquileres cobrados",
    "nota": "", "campos": [] }] }]
```

- Se cambia el diseño inicial (`contratos[]` con el inquilino dentro) por la propuesta de
  Alonso. Encaja con la realidad: el mismo inquilino renueva y lleva el historial de sus
  contratos. Varios inquilinos a la vez dejan la puerta abierta al alquiler por habitaciones.
- Los ids son únicos en toda la cartera (`q…`, `c…`). Así se editan y se borran por su id con
  el `GUARDAR`/`BORRAR` genérico (`/api/inquilinos`, `/api/contratos`).
- La ficha del inmueble los **conserva** al guardarse (`INMUEBLE_CONSERVA`). Editar un
  inquilino conserva sus contratos.
- **Datos propios (`campos`)**: lista de `{nombre, valores[]}` en el inquilino y en el
  contrato. Hasta 30 por ficha y 10 valores por dato. Los nombres no se repiten. En el
  formulario cada dato es una fila con «+ otro valor».
- El contrato valida: inicio obligatorio, fin posterior al inicio, renta > 0, día de cobro del
  1 al 31, actualización del catálogo (`ACTUALIZACIONES_CONTRATO`: ninguna, IPC, IRAV,
  pactada) y que la categoría del cobro sea **del propio inmueble**.

**A2. El contrato firmado, adjunto (pedido después).** Contrato e inquilino llevan
`archivos: [{tipo: "archivo"|"carpeta", id}]`, la misma forma que las notas, que apunta a
la **Biblioteca**:

- No se crea un almacén nuevo de archivos.
- Desde el formulario se **sube** el archivo. `/api/biblioteca/subir` acepta ahora
  `ruta`, una lista de carpetas que se crean si faltan. El archivo va a «Inmuebles /
  <inmueble> / Contratos» (o «Inquilinos»).
- También se puede **enlazar** uno que ya esté en la Biblioteca.
- **Formulario (rehecho tras la primera versión):** la primera metía el botón de subir, el
  desplegable y «Enlazar» en una sola fila bajo los chips, y parecían una misma cosa. Ahora
  hay una **lista** de lo adjunto arriba (una fila por documento, con «Quitar») y debajo
  **dos tarjetas separadas** por una «o»: «Subir desde tu ordenador» (zona de arrastrar y
  soltar, o pulsar; dice a qué carpeta va y muestra el progreso) y «Elegir de tu Biblioteca»
  (desplegable + «Enlazar»). En móvil se apilan.
- En la ficha salen como chips que lo abren. Como todo lo del inquilino, no viaja en
  `DATOS`.
- Si se cancela el formulario tras subir, el archivo se queda en la Biblioteca: está a la
  vista y se puede borrar desde allí.

**B. Cifras: renta, rentabilidad bruta y ocupación.**

- Un contrato está **vigente**, **firmado aún por empezar** o **terminado** según la fecha de
  hoy (o la de la foto de un mes pasado).
- **Renta mensual** = Σ de los contratos vigentes.
- **Rentabilidad bruta** = renta × 12 ÷ coste. Solo en los de inversión.
- **Ocupación** = inversión con contrato vigente ÷ inversión. Sin contratos anotados, manda
  su estado («alquilado»), para no castigar a quien aún no los ha metido. El total
  `alquilados` pasa a contar lo mismo.
- **Privacidad:** a `DATOS` solo van **cifras** (`alquiler: {inquilinos, contratos, vigentes,
  rentaMensual, proximoFin}`). Nombres, contactos y datos propios se leen de la cartera en vivo
  (`Editor.inquilinosInmueble`), como los documentos y los conceptos de los apuntes. En la web
  exportada la sección enseña solo ese resumen. `rentabilidadBruta`, `ocupacion` y los
  recuentos entran en `NO_DINERO`; la renta se escala.

**C. Batería de avisos (`motor.avisos_inmuebles`).**

| Clave | Cuándo | Plazo (por defecto) |
|---|---|---|
| `inm-fin-contrato` | Un contrato termina dentro del plazo, o terminó hace menos y no hay otro vigente ni firmado | 60 días |
| `inm-revision-renta` | Se acerca el aniversario de un contrato que se actualiza (no el día de inicio) | 30 días |
| `inm-cobro-proximo` | Se acerca el día de cobro de un contrato vigente (solo si tiene día de cobro) | 3 días |
| `inm-cobro-pendiente` | Pasado el día de cobro más el margen, **ningún ingreso** en la categoría del contrato (o en las de ingresos del inmueble) desde 25 días antes | 5 días de margen |
| `inm-valor-antiguo` | La estimación de valor tiene más de N meses | 12 meses |

- Van en `AVISOS_CATALOGO` con `grupo: "inmuebles"`. Se apagan con el mismo `avisosOff` de
  siempre. Sus plazos (`inmDias…`, `inmMesesValor`; vacío = por defecto, `AVISOS_INM_DEFECTO`)
  se configuran en **Configuración → 🏢 Inmuebles**, cada uno con su interruptor y su plazo al
  lado. El «Centro de avisos» general ya no los repite.
- Llevan `destino: {tab: "inmuebles", inmueble: id}`: al pulsarlos se abre **la ficha** del
  inmueble.
- Los textos nombran **el inmueble, nunca al inquilino**. No están en la foto de un mes pasado.
- El cobro se comprueba con **todos** los apuntes, también los archivados: un cobro archivado
  sigue cobrado.
- Sin categorías asociadas no se puede saber si se cobró, así que no avisa. El formulario del
  contrato lo explica.
- Heurística consciente: basta **un ingreso** cualquiera en la ventana. No se cuadra el importe,
  porque con varios contratos en una misma categoría daría falsos avisos.

**D. Filtro «Inmuebles» en Ingresos y gastos.**

- `flujosLista` lleva `inmueble` (por la categoría del apunte).
- El filtro ofrece: todos, «Sin los de inmuebles», «Solo los de inmuebles» o uno concreto. Se
  **recuerda** (`patrimonio.igInm`), porque lo normal es querer ocultarlos siempre. Uno ya
  borrado se ignora.
- Los filtros se reúnen en un único predicado (`filtroIg`) que usan `flujosSel` y
  `listaFlujosFiltrada`.
- **Arreglo de paso:** cambiar cualquier filtro solo repintaba la vista y no las cifras de
  arriba (`pintaFlujos`). Ahora usa `refrescaIg`.

**E. Panel con una cartera sin activos.**

- `construir` ya no devuelve `None` si hay inmuebles o apuntes. El eje queda en un solo día, la
  cartera en cero, y Inicio, Ingresos y gastos e Inmuebles funcionan.
- Verificado en vivo vista por vista, sin errores de JS.
- Sin nada de nada, sigue saliendo la invitación a empezar.

**F. Orden de Configuración.** La pestaña 🏢 Inmuebles pasa a la izquierda de 📄 Documentos.

**G. «— Sin categoría —» siempre en el filtro de Mis datos → Ingresos y gastos.** Antes
solo salía si algún apunte no tenía categoría (igual en `main`). Con todo clasificado
desaparecía, y parecía que se había perdido. Ahora sale siempre: elegirla y ver la lista
vacía confirma que todo está clasificado.

**H. La vivienda habitual bloquea lo que no le aplica (pedido después).** La habitual no se
alquila, así que en su formulario:

- **Estado**: queda deshabilitado y muestra «— no aplica —» (antes solo se ocultaba).
- **Categorías de ingresos**: se desmarcan y bloquean, con la nota «no van con la vivienda
  habitual». Sus gastos sí se asocian: son lo que cuesta vivir en ella.
- **Volver a inversión** recupera el estado y las casillas que había antes del cambio.
- **«Vivienda habitual» sale bloqueada** en el selector si ya lo es otro inmueble, con su
  nombre al lado. Antes solo lo avisaba un texto y el error al guardar.
- Una nota explica qué se bloquea y, si el inmueble tenía inquilinos, que se conservan.
- **Servidor** (por si llega por otra vía):
  - `guarda_inmueble` quita a la habitual las categorías de ingresos. El tipo se saca de
    `config.categorias` y, si no está, de sus apuntes (`_tipo_categoria`).
  - `inmuebles_de` no le calcula `alquiler`.
  - `avisos_inmuebles` no lanza los avisos de contrato ni de cobro; el de valor antiguo
    sí.

**I. Los chips de categorías de la ficha filtran su libro (pedido después).**

- Encima del libro, cada categoría del inmueble es un botón. Al pulsarlo, el libro se queda
  solo con sus apuntes: cifras, gráfica, tabla por categoría y apuntes.
- Se pueden pulsar varios y se suman. Los no elegidos se atenúan y aparece «✕ Todas».
- Se combina con el periodo; las cifras dicen «· N categorías».
- Es solo de la vista, con lo que ya trae `DATOS` (también en la web exportada). No se
  recuerda: se quita al abrir otro inmueble.
- Sin libro (ninguna categoría con apuntes) los chips siguen siendo informativos.

## Botón «i» (ADR 0020)

- `panel.inmuebles`: inquilinos y contratos, renta, bruta y ocupación, avisos y privacidad.
- `datos.inmuebles`: la ficha completa con sus inquilinos, más quién vive y la renta en la lista.
- `datos.config`: los avisos de inmuebles.
- `panel.ingresos`: el filtro «Inmuebles».
- Textos de ayuda en los formularios de inquilino y contrato y en la sección de avisos.

## Retrocompatibilidad

Aditivo. Sin `inquilinos` todo funciona igual (`alquiler: null`). La ocupación de quien no
tiene contratos usa su estado. La demo añade una inquilina con un contrato y datos propios.

## Pendiente

- Que la asociación siga a una categoría renombrada.
- ~~Migración de los productos `tipo:"inmueble"` de la cartera.~~ Hecha: ADR 0031.
- Fiscalidad del alquiler, histórico de valoraciones, TIR inmobiliaria.
- Avisos de IBI y seguro: hoy se cubren con un recordatorio anual de la agenda enlazado al
  inmueble.

## Tests

- **`pytest` 317** (+22 en `test_inmuebles_contratos.py`; entre ellos los documentos del
  contrato y del inquilino, la subida a la Biblioteca con `ruta` y la vivienda habitual sin
  ingresos, alquiler ni avisos de contrato):
  - inquilino con datos de varios valores y sus validaciones;
  - contrato y sus validaciones;
  - conservar inquilinos y contratos al editar; borrar;
  - plazos en la configuración;
  - renta, bruta y ocupación; contratos terminados o futuros;
  - cada aviso con su plazo, y que se pueden apagar;
  - `inmueble` en `flujosLista`;
  - Panel sin activos;
  - export oculto;
  - API.
- **`npm test` 22/22**:
  - el filtro «Inmuebles» (ocultar, uno solo, recordar, quitar);
  - renta y bruta en la ficha, sin datos personales sin editor;
  - el aviso que abre la ficha;
  - los recuentos de KPIs al día.
- **`ruff`** OK.
- **CDP**, sin errores de JS:
  - crear un inquilino con un dato de dos valores;
  - crear su contrato (recarga y cifras: renta 750 €, bruta 6,74 %);
  - los avisos de fin de contrato y de alquiler sin cobrar; pulsar uno abre la ficha;
  - la pestaña de avisos y el orden de pestañas;
  - el filtro en Ingresos y gastos;
  - claro, oscuro y móvil (sin scroll horizontal);
  - una cartera con solo un inmueble, recorriendo todas las vistas;
  - adjuntar dos PDF al contrato desde el formulario: se crea la carpeta, salen los chips y
    el archivo se abre (200, `application/pdf`);
  - el formulario rehecho: subir pulsando, soltar arrastrando (se resalta la zona), enlazar
    de la Biblioteca y quitar; guardado y visto en la ficha; claro, oscuro y móvil;
  - la vivienda habitual: estado y categorías de ingresos bloqueados y recuperados al volver
    a inversión, la opción bloqueada en otro inmueble y guardado sin estado;
  - «— Sin categoría —» en el filtro.
