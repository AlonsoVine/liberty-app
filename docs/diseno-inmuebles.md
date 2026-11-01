# Diseño — Zona de Inmuebles (rama `inmuebles`)

> Documento **vivo** de la rama `inmuebles`. Recoge lo acordado con Alonso y se actualiza en cada
> iteración. Al integrar en `main` se resumirá en un ADR y en el CHANGELOG de la release.

## Objetivo

Añadir una **tercera «app» dentro de Liberty**: la gestión de inmuebles, al mismo nivel que la
cartera (patrimonio) y que Ingresos y gastos. Hoy un inmueble solo puede ser un activo más de la
cartera, y eso tiene dos problemas:

1. **Descuadra los gráficos.** Un piso pesa tanto frente a fondos, cuentas o cripto que aplasta
   los donuts de distribución y las comparativas.
2. **No le cabe la gestión.** Un inmueble arrastra inquilinos, contratos, rentas, gastos
   recurrentes (IBI, comunidad, seguro…), hipoteca y mucho papeleo.

## Principios

- **Separación.** Los inmuebles no aparecen en los gráficos de la cartera.
- **Libro analítico.** Los ingresos y gastos del inmueble **no tocan el saldo de las cuentas**
  (igual que Ingresos y gastos; el saldo se ajusta a mano en Saldos).
- **Aditivo.** Una cartera anterior sigue funcionando igual. Los productos `tipo:"inmueble"` que
  ya existen en la cartera **conviven** sin migrar (ver «Fuera de alcance»).
- **100 % local**, como el resto de Liberty.

## Dónde vive en la interfaz

Mismo patrón que las otras dos apps: **se ve en Panel y se edita en Mis datos**.

| Sitio | Qué se añade |
|---|---|
| **Panel** | Grupo nuevo **«🏠 Inmuebles»**: resumen con KPIs, una tarjeta por inmueble y avisos propios |
| **Mis datos** | Grupo nuevo **«Inmuebles»**: lista y **ficha** de cada inmueble |
| **Ficha del inmueble** | Secciones: Datos · Compra y valor · Hipoteca · Contrato · Ingresos y gastos · Documentos |
| **Configuración** | Pestaña nueva **«🏢 Inmuebles»**: qué categorías van con cada inmueble |
| **Inicio** | Bloque **«Patrimonio total del hogar»** + mini-resumen de inmuebles |

Inicio es la vista que está por encima de las tres apps (cartera, ingresos y gastos, inmuebles).

## Modelo de datos

Colección nueva en la raíz de la cartera: `inmuebles: []`.

```jsonc
{
  "id": "in1",
  "nombre": "Piso Calle Mayor",
  "tipo": "piso",               // piso | casa | local | garaje | trastero | terreno | otro
  "titular": "Común",           // de los titulares existentes
  "uso": "inversion",           // inversion (por defecto) | habitual
  "estado": "alquilado",        // alquilado | vacio | reforma | venta   (solo si uso = inversion)
  "direccion": "", "refCatastral": "", "m2": 80, "habitaciones": 3, "valorCatastral": 60000,
  "compra": { "fecha": "2019-05-10", "precio": 150000, "gastos": 15000 },
  "valor": { "importe": 185000, "fecha": "2026-10-01" },   // estimación manual (la actual)
  "historico": [{ "fecha": "2025-06-01", "importe": 178000 }],   // las anteriores (ADR 0031)
  "hipoteca": {                  // opcional
    "capitalPendiente": 90000, "cuota": 650, "tipoInteres": 0.025, "fechaFin": "2044-05-10",
    "deudaRef": null             // id de un producto tipo "deuda" de Patrimonio (solo enlace)
  },
  "categorias": ["Alquiler · Piso Mayor", "Comunidad · Piso Mayor"],
  "inquilinos": [                // cada inquilino con sus contratos (ADR 0030)
    { "id": "q1", "nombre": "", "documento": "", "telefono": "", "email": "", "nota": "",
      "campos": [{ "nombre": "Avalista", "valores": ["Luis", "Marta"] }],   // datos propios
      "contratos": [
        { "id": "c1", "inicio": "2025-01-01", "fin": "2030-01-01", "renta": 900, "diaCobro": 5,
          "fianza": 900, "actualizacion": "irav",       // ninguna | ipc | irav | pactada
          "categoria": "Alquiler · Piso Mayor",         // dónde se apunta el cobro (opcional)
          "nota": "", "campos": [] }
      ] }
  ],
  "nota": ""
}
```

> El diseño inicial ponía `contratos[]` con el inquilino dentro. Se cambió a la propuesta de
> Alonso (el inquilino con sus contratos y datos propios de uno o varios valores): ver ADR 0030.

### Libro de ingresos y gastos: por categorías

El libro del inmueble **son los mismos apuntes de Ingresos y gastos**: no se duplica nada. Un
apunte cuenta para un inmueble cuando su **categoría** está asociada a ese inmueble.

- Se asocian en Configuración → «🏢 Inmuebles» (una o varias categorías por inmueble).
- **Una categoría pertenece como mucho a un inmueble.** La app lo valida.
- **Funciona hacia atrás:** al asociar una categoría, todos sus apuntes pasados cuentan.
- **Encadena con la importación:** las reglas `reglasCategoria` (palabra → categoría) clasifican
  el movimiento del banco y, por la categoría, va solo a su inmueble.
- Si se **renombra** una categoría, la asociación debe seguirla.
- En Ingresos y gastos se podrán **ocultar** los apuntes de inmuebles con un filtro.

### Hipoteca

Vive **dentro del inmueble** (fuente única). El campo opcional `deudaRef` solo **señala** que esa
hipoteca es una deuda que ya tienes en Patrimonio, con un botón para saltar a ella. No mueve
ningún número.

### Patrimonio total del hogar (Inicio)

`cartera − deudas + valor de los inmuebles − capital pendiente de las hipotecas`

Si una hipoteca está **enlazada** a una deuda (`deudaRef`), ya se resta en «deudas»: **no** se
vuelve a restar.

### KPIs

| KPI | Cálculo | Inversión | Habitual |
|---|---|---|---|
| Valor total | Σ valor estimado | ✔ | ✔ |
| Revalorización | valor estimado − (precio + gastos de compra), solo si hay estimación | ✔ | ✔ |
| Neto inmobiliario | valor − capital pendiente de las hipotecas | ✔ | ✔ |
| Renta mensual | Σ renta de los contratos activos | ✔ | — |
| Rentabilidad bruta | renta anual ÷ (precio + gastos de compra) | ✔ | — |
| Cash-flow neto | ingresos − gastos del libro (apuntes reales) | ✔ | — |
| Rentabilidad neta | cash-flow anual ÷ (precio + gastos de compra) | ✔ | — |
| Ocupación | inmuebles alquilados ÷ inmuebles de inversión | ✔ | — |
| Coste anual | gastos del libro en los últimos 12 meses | ✔ | ✔ |

> **Ojo con el doble conteo:** si la cuota de la hipoteca ya se apunta como gasto en una categoría
> del inmueble, el cash-flow la incluye. Los datos de la hipoteca de la ficha son **informativos**
> y no se restan otra vez. (La parte de la cuota que amortiza capital no es un gasto real: se
> afinará al tratar la fiscalidad).

## Iteraciones

1. ✅ **Núcleo** *(hecha, ADR 0028)*. Colección `inmuebles` + validación en `almacen.py` + API +
   ficha en Mis datos (datos, compra, valor, uso, hipoteca con enlace opcional) + vista del
   Panel (valor estimado, revalorización, hipotecas, neto) + demo + tests.
   - Cambios respecto al plan: la **rentabilidad bruta pasa a la iteración 2** (necesita la renta
     de los contratos). Los ids son `i1, i2…` (`siguiente_id` solo admite prefijos de una
     letra). Sin valor estimado, la revalorización es **desconocida**, no negativa. Una deuda
     solo puede enlazarse a un inmueble.
   - **Limitación conocida:** sin ningún activo con datos, el motor no calcula el Panel (le pasa
     igual a Ingresos y gastos). Se revisará en la iteración 4.
2. ✅ **Contratos e inquilinos** *(hecha, ADR 0030)*. Inquilinos con sus contratos y datos
   propios en la ficha. Renta mensual, **rentabilidad bruta** y ocupación.
3. ✅ **Libro por categorías** *(hecha, ADR 0029)*. Pestaña «🏢 Inmuebles» en Configuración
   (un selector de inmueble por categoría) y casillas en la ficha, cash-flow y rentabilidad
   neta a 12 meses y coste de la vivienda habitual aparte.
   - ✅ Filtro «Inmuebles» en Ingresos y gastos *(ADR 0030)*.
   - **Pendiente:** la asociación **no sigue** a una categoría renombrada, porque las categorías se editan como
     texto y no hay renombrado como tal: hay que volver a asociarla. Las que ya no existen se
     ven como «Otras» y se conservan.
4. ✅ **Inicio** *(hecha, ADR 0029)*. Bloque «Tus inmuebles» con el patrimonio total del hogar
   y la lista de inmuebles. Sin inmuebles, una invitación a la zona. ✅ Con una cartera sin
   activos (solo inmuebles o apuntes) el Panel ya se calcula *(ADR 0030)*.
5. **Documentos y avisos.** ✅ Documentos *(ADR 0029)*: vínculo `inmueble` en las notas, sección
   en la ficha con nota nueva, enlazar una existente y quitar el enlace. ✅ Avisos *(ADR 0030)*:
   fin de contrato, revisión de la renta, cobro que se acerca, alquiler sin cobrar y valor
   antiguo, configurables en Configuración → 🏢 Inmuebles. IBI y seguro: con un recordatorio
   anual de la agenda enlazado al inmueble.

**Ficha ampliada** *(ADR 0029)*: vive en el Panel, en Inmuebles, y es de solo lectura. Reúne
los datos, la compra y el valor, la hipoteca, el libro y los documentos. Se edita con
«✎ Editar ficha», que guarda y recarga. El libro lleva un **selector de periodo**: 12 meses,
este año, el año pasado, todo o un rango de una fecha a otra.

Cada iteración: botón «i» de cada pantalla nueva (ADR 0020), tests (`pytest` + `jsdom`),
verificación en vivo por CDP y el export estático sin romper.

## Fuera de alcance (por ahora)

- ~~**Migración** de los productos `tipo:"inmueble"` de la cartera a la zona nueva.~~ ✅ Hecha
  como **traspaso completo**, con historial de valoraciones y evolución del valor en la ficha
  *(ADR 0031)*.
- **Alquiler por habitaciones** (varios contratos a la vez en un inmueble). Los contratos ya son
  una lista para no cerrar la puerta.
- **Ajuste por apunte** para excepciones (una categoría genérica usada para varias cosas).
- **Fiscalidad:** rendimiento neto del capital inmobiliario, amortización del 3 %, reducciones
  por alquiler de vivienda, imputación de renta de los vacíos.
- **Histórico de valoraciones**, TIR de la inversión inmobiliaria, comparativa entre inmuebles.

## Integración

Se itera en la rama y **solo se integra en `main` como release nueva cuando esté lista**.
