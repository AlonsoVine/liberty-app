# ADR 0038 — Mejora estética integral

- **Estado:** aceptado (publicado en v1.20.0)
- **Fecha:** 2026-11-07

## Contexto

La interfaz funcionaba, pero tenía varios problemas visuales y de accesibilidad:

- aspecto genérico, con emojis usados como iconos;
- contraste por debajo de WCAG AA en muchos textos (axe: 1093 nodos con fallo);
- saltos de maquetación al cargar (CLS 0,975);
- desplazamiento lateral en móvil.

Alonso encargó una mejora estética de nivel alto, con estas condiciones:

- sin cambiar la funcionalidad, los datos ni el contenido;
- sin dependencias nuevas;
- que funcione sin conexión.

## Decisiones

El proceso y la puntuación de cada vuelta están en `docs/estetica/DECISIONES.md` y `docs/estetica/REVISIONES.md`, con capturas de antes y después.

- **Tipografía:** Geist para la interfaz y Fraunces para los títulos y las cifras protagonistas, servidas en local.
- **Iconos de línea propios:** un iconizador sustituye los emojis usados como icono. El texto no cambia.
- **Cifras como libro de cuentas:**
  - «Tu cartera hoy» son dos ecuaciones (bruta − deudas = neta y disponible − reservados − colchón = libre).
  - Distribución, Inicio e Inmuebles muestran sus cifras en filas y franjas con filete.
- **Movimiento solo con transform y opacity:**
  - una regla global limita las transiciones a esas dos propiedades;
  - las cifras grandes se animan con un odómetro y el cambio de tema con View Transitions;
  - con «reducir movimiento» no hay animación.
- **Color:**
  - `--acento-fondo` para los fondos de botón con texto blanco;
  - signo menos tipográfico (U+2212);
  - variaciones nulas en color neutro.
- **Móvil:**
  - sin desplazamiento lateral entre 360 y 1920 px;
  - las tablas de Saldos y valores caben enteras, sin desplazamiento interno, a petición de Alonso.

## Consecuencias

Resultados:

| Medida | Antes | Después |
|---|---|---|
| Nodos con fallo en axe | 1093 | 0 |
| CLS | 0,975 | 0,001 |
| Lighthouse escritorio | 61 | 90 |
| Lighthouse móvil | 30 | 57 |

La funcionalidad no cambia y los tests siguen pasando.

El árbitro independiente dio 7,15–7,30 en las tres últimas vueltas. No llegó al listón de 8,5 que se había fijado.

Cualquier estilo nuevo debe:

- respetar la regla de transiciones;
- usar los tokens de color (`--acento-fondo` cuando el texto va en blanco);
- no reintroducir emojis como icono fuera del mapa del iconizador.
