# ADR 0017 — Empaquetado y distribución multiplataforma (Windows + macOS)

- **Estado:** aceptado
- **Fecha:** 2026-10-19
- **Fase:** distribución (desde la versión 1.11.2)

## Contexto

Hasta ahora Liberty solo se distribuía como `Liberty.exe` (Windows). Se añade soporte para
**macOS** manteniendo la filosofía: 100 % local, sin instalación ni dependencias para el usuario.

## Decisiones

**1. Carpeta de datos por plataforma** (`servidor.py` `_base_datos`). Windows empaquetado:
`mis_datos` **junto al ejecutable** (portable, como siempre). macOS: un `.app` es de **solo
lectura** (más aún en `/Aplicaciones` o en la cuarentena de Gatekeeper), así que los datos van a
**`~/Library/Application Support/Liberty`**, que persiste aunque muevas o reinstales la app. Sin
empaquetar, la carpeta del proyecto (igual en todos los sistemas).

**2. Empaquetado Mac** (`Liberty-mac.spec`). PyInstaller en modo *onedir* + `BUNDLE` → un
**`Liberty.app`** con `console=False` (aparece en el Dock y se sale con «Salir»), icono `.icns` y
`bundle_identifier=com.alonsovine.liberty`. **Sin firmar**: la primera vez el usuario lo abre con
**clic derecho → «Abrir»** (o desde Ajustes del Sistema → Privacidad y seguridad). Firma y
notarización quedan pendientes (requieren cuenta de Apple Developer de pago). Se compila para
**Apple Silicon (arm64)**; el soporte Intel (`universal2` o un runner macos-13) queda como mejora
futura.

**3. Build en integración continua** (no se puede compilar Mac desde Windows). Workflow
`.github/workflows/build-mac.yml` en el repo del **código** (`AlonsoVine/rumboExito`), runner
`macos-latest`: instala dependencias, genera el `.icns` (`sips` + `iconutil`), compila, hace un
**smoke test** (arranca el `.app` y hace `curl` a `/` y `/api/version`), comprime con `ditto` a
**`Liberty-macOS.zip`**. Es `workflow_dispatch` (manual, con input `tag`) porque las Releases viven
en el repo de **distribución** (`AlonsoVine/liberty`), no en `rumboExito`, así que un
`release: published` sería de otro repo. Sube el asset a la release de `liberty` **solo si existe el
secreto `LIBERTY_RELEASE_TOKEN`** (un PAT con escritura en `liberty`); si no, lo deja como
**artefacto** del run para subirlo a mano. Consecuencia de repo: la rama por defecto de `rumboExito`
pasó a `main` al día (`workflow_dispatch` exige el workflow en la rama por defecto) y se
consolidó el trabajo en una sola rama `main`.

**4. Actualización in-app en Mac.** `api/descargar-version` **no** auto-descarga en macOS
(reemplazar un `.app` en marcha es delicado): dirige a la web. El chequeo de versión (banner «hay
versión nueva») funciona igual en ambos sistemas.

**5. Distribución** (repo `liberty`). La landing ofrece **dos descargas** (`Liberty.exe` /
`Liberty-macOS.zip`) con los avisos de SmartScreen (Windows) y Gatekeeper (Mac). El contador de
descargas suma el `download_count` de **ambos** assets en todas las releases. Regla (en el
`CLAUDE.md` de la landing): nombres de asset **exactos**, una **release nueva** por versión, nunca
borrar releases antiguas ni re-subir encima de un asset ya publicado (se perdería su contador).

## Retrocompatibilidad

Windows sin cambios: misma ruta de datos (`mis_datos` junto al `.exe`) y mismo empaquetado. macOS
es una plataforma nueva.

## Tests

Smoke test del `.app` en el runner de macOS (home `200`, `api/version` con la versión correcta) como
paso del propio workflow. En Windows, `pytest`/`ruff`/jsdom siguen verdes: los cambios de
`servidor.py` son multiplataforma y no alteran el camino de Windows.
