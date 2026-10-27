# Liberty en Docker — una sola instancia para toda la casa (p. ej. en una Raspberry Pi, arm64),
# accesible SOLO por tu red privada o VPN (nunca expuesta a internet). Imagen multiarch
# (linux/amd64 + linux/arm64). La base se fija por DIGEST del manifest multiarch, no solo por
# tag, para que la imagen sea reproducible. El mismo código sirve para .exe, .dmg y Docker.
FROM python:3.12-slim-bookworm@sha256:6dd8b6dab6b3adc7812bab69eca5dbdc1a5cc690ad28306d234ffb4ef8ac9753

# Qué cambia en Docker (lo lee app/entorno.py): datos en /data (un volumen), escucha en todas
# las interfaces DEL CONTENEDOR (el puerto se publica solo en 127.0.0.1 del anfitrión vía
# compose), modo docker y sin abrir navegador.
ENV LIBERTY_DATOS=/data \
    LIBERTY_HOST=0.0.0.0 \
    LIBERTY_PUERTO=8765 \
    LIBERTY_MODO=docker \
    PATRIMONIO_NO_ABRIR=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencias primero (capa cacheable). Sin compiladores: todo son ruedas, también en arm64.
COPY requirements-docker.txt ./
RUN pip install --no-cache-dir -r requirements-docker.txt

# Código y recursos de solo lectura (web, demo, VERSION, prompts). Los DATOS no van en la
# imagen: viven en el volumen /data. (.dockerignore excluye mis_datos, .git, tests, dist…)
COPY app/ ./app/
COPY demo/ ./demo/

# Usuario sin privilegios (uid 1000). El dueño de /data se ajusta en el anfitrión
# (chown -R 1000:1000 <carpeta>); si usas otro uid, cámbialo también en el compose.
RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin liberty \
    && mkdir -p /data && chown liberty:liberty /data
USER liberty

EXPOSE 8765
VOLUME ["/data"]

# Salud: la imagen slim NO trae curl ni wget; usamos la stdlib de Python contra el propio
# puerto (127.0.0.1 siempre está permitido por la validación de Host). Así no añadimos curl
# (menos superficie y menos peso). /api/ping no sale a la red.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('LIBERTY_PUERTO','8765')+'/api/ping',timeout=4).read()"]

# python -m app -> app/__main__.py -> servidor.main() (detecta Docker y sirve con waitress).
ENTRYPOINT ["python", "-m", "app"]
