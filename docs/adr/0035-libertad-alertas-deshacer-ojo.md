# ADR 0035 — Libertad financiera, alertas de precio, «Deshacer» al borrar y 👁

- **Estado:** aceptado (publicado en la 1.19.0)
- **Fecha:** 2026-11-03
- **Fase:** mejoras de UI/UX propuestas tras la 1.18.0 (las n.º 1, 8, 12 y 13 de la lista)

## Contexto

Antes de proponerlas se comprobó que no existían: no había ningún cálculo de «meses que
vivirías» ni de independencia financiera, ni alertas de precio por activo. Deshacer solo existía
como «Deshacer el último cambio» en Copias, y «Ocultar importes» solo en Ajustes.

## Decisiones

### 1. Tu libertad financiera (`motor.libertad_financiera`, `DATOS.libertad`)

- **Gasto medio:** la media de los meses **completos** (sin el mes en curso, que va a medias)
  desde el primero con apuntes, hasta 12. Sin un mes completo → `None` y la card invita a
  anotar. El mes en curso es el de **hoy** (o el del mes pasado que se está viendo), no el del
  último dato: si no anotas nada en octubre, octubre cuenta como un mes sin gastos.
- **Meses con lo disponible** = disponible (liquidez marcada) / gasto medio.
- **Meses con toda tu cartera** = cartera / gasto medio. La cartera es la de la card «Tu
  patrimonio»: la hipoteca enlazada va con su casa.
- **Independencia financiera** = renta pasiva / gasto medio, donde renta pasiva = cartera ×
  tasa de retirada / 12 + alquileres. Los alquileres son la renta de los contratos vigentes o,
  si no hay contratos, lo cobrado de media en 12 meses. Se usa la renta **bruta**: los gastos del
  inmueble ya están dentro del gasto medio, así que la neta los restaría dos veces.
- **Tasa de retirada:** `config.tasaRetirada`. Vacía = 4 %, máximo 20 %.
- **Cartera objetivo** = (gasto − alquileres) × 12 / tasa. Se llama `carteraObjetivo` y no
  `objetivo` porque `objetivo` se elimina en la web exportada.
- **Interfaz:** card en Inicio bajo «Tu patrimonio», con tres celdas (dos de tiempo y el % con su
  barra) y una nota que dice que es una orientación sin impuestos ni inflación. Los meses se
  muestran en días por debajo de un mes y en años desde 24 meses.

### 2. Alertas de precio (`cfg.alertasPrecio`, `motor.alertas_precio`)

- **Formato:** `{id, producto, condicion, valor, ref?, refFecha?, nota?}`.
  - `condicion` ∈ `cae | sube` (% desde `ref`, guardado como fracción) o `menor | mayor`
    (importe).
  - Se vigila el **precio** (`nav`) de lo que cotiza y el **valor** de lo que va a mano.
- **Ciclo de vida:** CRUD por las rutas genéricas (`POST /api/alertas`, `DELETE
  /api/alertas/<id>`). Se borran con su producto.
- **Aviso:** una alerta cumplida es un aviso del motor (`clave: "alerta-precio"`, apagable desde
  el catálogo de avisos), con `destino: {tab:"producto", producto}`. En el Panel abre la ficha.
  No salta al ver un mes pasado.
- **Comparación sin ruido:** la variación se redondea a 9 decimales. 90/100 debe «caer justo un
  10 %» y en coma flotante no lo hacía. El front hace lo mismo.
- **Ficha del activo:** bloque «🔔 Alertas de precio» con su estado (`se cumple` / `vigilando ·
  ahora ±x %`) y botones para crear, editar y quitar. El formulario está en editor.js
  (`Editor.editarAlerta/borrarAlerta`) y repinta la ficha sin recargar.
- **Web exportada:** no hay edición. `alertasPrecio` se quita de la versión sin importes; los
  textos de los avisos ya enmascaran los «€».

### 3. «Deshacer» justo después de borrar

- **Un único hueco en memoria (`_DESHACER`)** con la cartera tal como estaba antes del último
  borrado, guardada en `cambia(…, deshacible=True)`. Hay borrado individual, de varios y «todo lo
  anterior a una fecha». La respuesta trae un `deshacer` (token aleatorio). Cualquier otro cambio
  hecho con `cambia` vacía el hueco.
- **`POST /api/deshacer {token}`** solo restaura si se cumplen todas estas condiciones:
  - el token coincide;
  - han pasado menos de 10 minutos;
  - la cartera activa es la misma;
  - el fichero no ha cambiado desde el borrado (se compara la huella JSON). Así se cubre
    también lo escrito por otra vía o desde otro dispositivo.

  Si alguna falla, responde 409 y remite a Copias. Nunca pisa nada.
- **Facturas:** al borrar un apunte se renombran para encontrarlas. «Deshacer» las devuelve a su
  nombre para que el apunte recuperado las siga teniendo.
- **Interfaz:** `toast(msg, tipo, {texto, fn})` admite un botón. Con botón dura 8 s y responde a
  Ctrl+Z si el foco no está en un campo. El texto «No se puede deshacer» del borrado por fecha
  pasa a mencionar «Deshacer».

### 4. 👁 en la barra superior

- **El botón** cambia la misma preferencia `patrimonio.ocultar` que Ajustes (🙈 = ocultos) y
  repinta el Panel y Mis datos.
- **Mis datos:** su `eur()` ahora también respeta `OCULTAR_IMPORTES`.
- **Web exportada sin importes:** el botón no aparece, porque ahí no se pueden volver a mostrar.

## Privacidad

Todo es local. La web exportada con «Ocultar importes» escala los euros de `libertad` y deja tal
cual los meses, el progreso y la tasa (`NO_DINERO`). Las alertas no viajan. El hueco de deshacer
vive solo en la memoria del servidor.

## Botón «i» (ADR 0020)

- `panel.inicio`: «🕊️ Tu libertad financiera».
- `panel.producto`: «🔔 Alertas de precio».
- `datos.flujos`: «↩️ ¿Te has equivocado? Deshacer» (y el borrado por fecha).
- `datos.saldos`: borrar varios, con Deshacer.
- `datos.config`: «🕊️ Tasa de retirada».
- `datos.copias`: «↩️ Deshacer».
- `ajustes`: «Ocultar importes», con el 👁.

## Retrocompatibilidad

Aditivo: campos nuevos opcionales (`alertasPrecio`, `config.tasaRetirada`) y en DATOS
(`libertad`, `alertasPrecio`). `siguiente_id` ahora admite prefijos de más de una letra (antes
asumía una; con «al» habría fallado).

## Tests

- **`pytest` 345** (+14), sobre:
  - el gasto medio sin el mes en curso;
  - los alquileres y la tasa de retirada;
  - el caso sin datos;
  - que `construir` publica la libertad;
  - la validación de la tasa;
  - las alertas por %, por importe y a mano;
  - el CRUD de alertas y su borrado en cascada;
  - el aviso y cómo apagarlo;
  - que deshacer recupera también las facturas y solo funciona una vez;
  - que no deshace tras otro cambio, con un token ajeno ni con una escritura externa;
  - que guardar no ofrece deshacer;
  - `siguiente_id`.
- **`npm test` 29/29** (+4):
  - la card de libertad y su estado vacío;
  - el 👁, que no aparece en la web exportada sin importes;
  - el aviso con «Deshacer» por clic y por Ctrl+Z;
  - que el aviso de una alerta abre la ficha con sus alertas.
- **Prueba en vivo (CDP, claro y oscuro):**
  - la card con datos reales;
  - el 👁;
  - crear, quitar y deshacer una alerta;
  - una alerta cumplida que sale en el banner y abre la ficha;
  - sin errores de JS.
