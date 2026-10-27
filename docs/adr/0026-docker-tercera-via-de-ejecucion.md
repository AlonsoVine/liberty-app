# ADR 0026 — Docker como tercera vía de ejecución (NAS/Raspberry Pi) y endurecimiento del servidor

- **Estado:** aceptado
- **Fecha:** 2026-10-27
- **Fase:** infraestructura (próxima versión 1.16.0)

## Contexto

Liberty se distribuye como `Liberty.exe` (Windows) y `Liberty-macOS.dmg` (Mac). Alonso quería una
**tercera forma de ejecutarlo: en Docker**, para correr una **única instancia en casa** —una
Raspberry Pi 4 (`linux/arm64`) como NAS— a la que la familia accede desde varios dispositivos por
**Tailscale** (`tailscale serve`), nunca desde internet, y actualizar con `docker compose pull`.
Prioridad declarada: **seguridad y privacidad máximas**. Requisito firme: **no romper nada** de lo
actual (`.exe`/`.dmg`, actualizador, datos en `mis_datos/`, web y publicación) y que **el mismo
código** sirva para las tres vías (sin ramas ni forks).

## Decisiones

**A. Punto único de entorno (`app/entorno.py`).** Módulo nuevo, sin dependencias de la app, que
decide a partir de variables de entorno lo que cambia entre vías: `DATOS` (`LIBERTY_DATOS`, alias
retrocompatible `PATRIMONIO_DATOS`), `HOST` (`LIBERTY_HOST`, default `127.0.0.1`), `PUERTO`
(`LIBERTY_PUERTO`/`PATRIMONIO_PUERTO`), `HOSTS_PERMITIDOS`, `ES_DOCKER` (marca `LIBERTY_MODO=docker`
o `/.dockerenv`) y `NO_ABRIR`. El escritorio mantiene exactamente el comportamiento de siempre.
La Fase 3 (elegir carpeta de datos en el escritorio) reutilizará este mismo punto.

**B. Servidor de producción y cierre limpio (`servidor.py`, `main()`).** En Docker se sirve con
**waitress** (un solo proceso, pool de hilos) vía `create_server`, y se registran manejadores de
**SIGTERM/SIGINT** que cierran el servidor —waitress no lo hace por su cuenta y Python como PID 1 lo
ignoraría—, de modo que `docker stop` sale limpio (~0,4 s, código 0) en vez de esperar 10 s y matar
el proceso. En escritorio sigue el servidor de Werkzeug (`make_server`), que ya ganó también un
manejador de SIGTERM. Un solo proceso + el `RLock` de siempre + `os.replace` atómico ⇒ varios
clientes a la vez no corrompen ficheros.

**C. Endurecimiento del acceso (`servidor.py`, `_solo_local`).** La allowlist de `Host`
(anti-DNS-rebinding) pasa a ser `{127.0.0.1, localhost, ::1} ∪ LIBERTY_HOSTS_PERMITIDOS`, por
**coincidencia exacta sin comodines** (un `*.ts.net` reabriría el rebinding; el usuario pone el
nombre completo de su nodo Tailscale). Se añade **defensa CSRF por Origin/Referer** en los métodos
que mutan: si llega `Origin`/`Referer` y su host no está en la allowlist → 403. Tras `tailscale
serve` el TLS se termina fuera y se preserva el `Host`, así que encaja.

**D. Guard de cartera activa (`servidor.py`, `cambia()`).** La cartera activa es estado global: si
un dispositivo la cambia mientras otro edita, la escritura del segundo iría a la **cartera
equivocada**. El front envía la cabecera **`X-Cartera`** con la cartera que cree activa; si ya no
coincide con la real → **409** sin escribir, y el front recarga. Sin cabecera, comportamiento de
siempre.

**E. Actualizador y ruta de datos en la UI.** `/api/descargar-version` en Docker responde
`motivo:"docker"` con las instrucciones `docker compose pull && docker compose up -d`; el banner y
el pie de versión lo reflejan (sin botón de descarga). Nuevo `/api/entorno` → `{docker, rutaDatos,
puedeCambiarRuta:false}`; en **Ajustes** se muestra la carpeta de datos en **solo lectura**.

**F. Empaquetado y publicación.** `Dockerfile` (base `python:3.12-slim-bookworm` fijada por
**digest** del manifest multiarch; usuario no-root uid 1000; `HEALTHCHECK` con la **stdlib de
Python** porque la imagen slim no trae `curl`; rootfs apto para solo lectura), `.dockerignore` (la
imagen lleva **solo código**, nunca datos ni secretos), `docker-compose.yml` endurecido de ejemplo
(puerto solo en `127.0.0.1`, `read_only` + `tmpfs`, `cap_drop: [ALL]`, `no-new-privileges`, `init`,
`user` ajustable, tag de versión fijo) y `requirements-docker.txt` (añade waitress). Al arrancar en
Docker, `prepara_datos_docker()` crea el centinela `/data/.liberty`, **avisa si el volumen está
vacío** (posible disco sin montar) **sin borrar nada**, y sella la versión de los datos. El
workflow `docker.yml` publica en **GHCR** multiarch (amd64+arm64), con **smoke en ambas
arquitecturas** (arm64 bajo QEMU) antes de publicar y las acciones de terceros **fijadas por SHA**;
solo `workflow_dispatch` (las releases viven en el repo de distribución, así que `on: release` no
aplica).

**G. Visibilidad y licencia.** Repo e imagen **públicos** (la privacidad de los datos la da el
diseño del despliegue, no la visibilidad del repo). La imagen es *source-available* bajo la
**licencia híbrida** (MIT para «Rumbo» + propietario/uso personal para Liberty). Se corrige la
landing (`liberty/LICENSE` y `README.md`), que declaraba MIT total, incoherente con el código.

## Botón «i» (ADR 0020)

Se actualiza la ayuda de **Ajustes**: nuevo punto «📂 Carpeta de datos» (y nota de que en Docker la
fija el volumen) y matiz en «🔄 Buscar actualizaciones» (en Docker explica actualizar la imagen).

## Retrocompatibilidad

Todo aditivo. Sin variables de entorno nuevas, el escritorio se comporta igual (host `127.0.0.1`,
datos en `mis_datos/`, navegador que se abre, actualizador que descarga el binario). `PATRIMONIO_*`
se mantiene como alias. El guard de cartera solo actúa si el front manda `X-Cartera`. Volver a una
imagen anterior es seguro: las migraciones solo reordenan ficheros, no cambian su formato.

## Tests

`pytest` (incluye `test_entorno_docker.py` y el guard de cartera en `test_multicartera.py`) y
`npm test` 14/14 en verde. Verificación en vivo con Docker (amd64): build, `/api/ping` con versión y
modo, allowlist de Host (403 ajeno / 200 permitido), `/api/entorno`, crear cartera, **persistencia
tras reinicio** y **cierre limpio** por SIGTERM (0,4 s, código 0). `ruff` no se pudo ejecutar en la
máquina (binario ausente); el CI lo pasa en cada push.
