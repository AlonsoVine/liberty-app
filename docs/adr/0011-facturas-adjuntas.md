# ADR 0011 — Facturas adjuntas a ingresos y gastos

- **Estado:** aceptado
- **Fecha:** 2026-10-14
- **Fase:** mejoras post-F4 (ingresos y gastos)

## Contexto

Se quería poder **adjuntar la factura o el ticket** a un apunte de ingreso/gasto y,
además, **reunir todas** las facturas en un sitio y destacar las importantes, sin que
la app deje de ser **100 % local**.

## Decisión

Los **archivos viven en disco**, en una carpeta `adjuntos/` dentro de la cartera
(`carteras/<id>/adjuntos/`); la `cartera.json` solo guarda **referencias**: cada
apunte gana `adjuntos: [{id, archivo, nombre, tipo, tam, importante?}]`.

- **Nombre en disco** = `adj_<hex aleatorio><ext>` (no se confía en el nombre
  original, que se guarda solo como `nombre` para mostrar) → sin traversal.
- **Formatos**: PDF e imágenes (jpg/png/webp/heic/gif). **Límite 15 MB** por archivo
  (se comprueba tras guardar y se borra si se pasa).
- **Endpoints** (Flask, local, sin red): `POST /api/flujo-adjunto` (multipart, guarda
  el archivo y anota la referencia), `POST /api/flujo-adjunto-quitar` (borra referencia
  y archivo), `POST /api/flujo-adjunto-importante`, y `GET /api/adjunto/<flujo>/<id>`
  (sirve el archivo *inline*; solo sirve lo referenciado en la cartera).
- **Limpieza**: al borrar un apunte se borran sus archivos (en `api_borrar`); al editar
  un apunte por el formulario se **conservan** los adjuntos (el form no los manda).
- **UI**: columna `📎` en la tabla (indicador + gestor en modal para subir/abrir/marcar/
  quitar), filtro «con/sin factura», y una vista **«Facturas»** (sub-pestaña de Mis
  datos) que reúne todas, con buscador y «solo importantes ★».

**NO** se mete el archivo en el JSON (base64): unas pocas facturas dispararían el
tamaño de `cartera.json` y ralentizarían cada carga/guardado.

## Alternativas descartadas

- **Base64 dentro de `cartera.json`**: descartado por peso/rendimiento.
- **Carpeta global de adjuntos** (fuera de la cartera): se prefiere por-cartera, para
  que copiar la carpeta de una cartera se lleve también sus facturas.
- **Gestionar los adjuntos desde el formulario del apunte**: el formulario guarda JSON;
  las subidas son multipart y asíncronas. Se gestionan aparte (columna 📎 / vista
  Facturas) y el formulario solo los conserva.

## Consecuencias

- Aditivo y retrocompatible: apuntes sin `adjuntos` funcionan igual.
- **Copias de seguridad**: la copia de un solo `.json` **no** incluye los archivos;
  copiar toda la carpeta `mis_datos` sí. Pendiente (acordado): ofrecer en «Exportar»
  una segunda opción que genere un **.zip** (JSON + adjuntos). Se avisa en la Ayuda y
  en «Copias y seguridad».
- Añade subida/servido de archivos (Flask estándar); no introduce `subprocess`/`exec`
  ni red externa (no cambia el perfil frente a los antivirus).
