# ADR 0036 — Inicio a tu gusto

- **Estado:** aceptado (publicado en la 1.19.0)
- **Fecha:** 2026-11-03
- **Fase:** mejoras de UI/UX, la n.º 14 de la lista

## Contexto

Inicio tenía un orden fijo de cards. Se quería poder ordenarlas, ocultarlas y poner algunas a
media anchura, además de un modo compacto. Alonso eligió tres cosas:

- cambiarlo **desde el propio Inicio**, con un botón «Personalizar»;
- guardarlo **en la cartera**, de modo que sea el mismo Inicio en todos los dispositivos y para
  toda la familia, también en Docker;
- como extras, el **tamaño** de cada card y el **compacto**.

## Decisiones

- **Ocho bloques con id**, en este orden de fábrica: `patrimonio`, `libertad`, `banda` (cartera
  en el tiempo y objetivo), `constancia`, `cartera`, `ingresos`, `inmuebles` y `archivo`.
  - `pintaInicio` construye un mapa `B[id] = html` y `montaInicio` los coloca según la
    disposición.
  - Un bloque sin contenido (por ejemplo, Ingresos sin apuntes) no se pinta y no cuenta al mover.
  - Cada bloque va en `div.inicioBloque[data-bloque]`.
- **Formato:** `config.inicio = {orden, ocultas, medias, compacto}`.
  - Se guarda con `/api/config`; `almacen.guarda_config` sanea los ids contra `BLOQUES_INICIO` y
    quita repetidos.
  - `inicio: None` vuelve al de fábrica.
  - Llega al Panel en `DATOS.inicio`.
- **Cards nuevas en versiones futuras:** si al orden guardado le falta alguna, se coloca tras la
  que la precede en el orden de fábrica. Así nadie la pierde.
- **Rejilla:** `#inicioCuerpo` es una rejilla de dos columnas.
  - Una card ancha ocupa las dos; una «media» ocupa una.
  - Con 900 px o menos, todas van anchas.
  - A media anchura, el contenido interior se apila.
  - El espacio entre cards lo pone la rejilla: se anulan los márgenes propios de cada card.
- **Compacto:**
  - se ocultan gráficos, leyendas y notas, y queda la cifra principal (el aro de constancia sí,
    porque es la cifra);
  - los gráficos ocultos **ni se dibujan**.
- **Modo edición:** se abre con «✎ Personalizar».
  - Cada card lleva una barra con ⋮⋮ (arrastrar y soltar, delante o detrás según la mitad), 👁
    (ocultar; la card se ve en gris mientras se edita), ↔ (ancho) y ↑ ↓ (con teclado y en
    móvil).
  - Arriba está el interruptor «Compacto», «Restablecer» (pide confirmación) y «Listo».
  - El contenido de las cards no responde mientras se edita.
  - Cada cambio se guarda solo, agrupado en 500 ms. Si falla (por ejemplo, en la demo), avisa y
    deja la vista local.
- **Web exportada:** respeta la disposición, pero no hay botón para editarla.

## Botón «i» (ADR 0020)

- `panel.inicio`: «✎ Personaliza tu Inicio».

## Retrocompatibilidad

Aditivo: sin `config.inicio`, Inicio sale como siempre. Las cards van ahora dentro de
`.inicioBloque`, y los tests de render se adaptaron a ello.

## Tests

- **`pytest` 347** (+2): el saneado, que guardar otra cosa no toca la disposición, el
  restablecer, una disposición no válida y que `construir` la publica.
- **`npm test` 30/30** (+1):
  - el orden, las ocultas, las medias y el compacto guardados;
  - la card nueva colocada en su sitio;
  - el modo edición: ver la oculta, mostrarla, subir, cambiar el ancho y quitar el compacto;
  - un único guardado agrupado con la disposición final.
- **Prueba en vivo (CDP, claro y oscuro):** dos cards lado a lado con el mismo alto, ocultar,
  persistir al recargar, el compacto (sin gráficos) y restablecer, sin errores de JS.
