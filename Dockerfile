# Tala X web API: the analysis core, ExifTool and the FastAPI server.
# Runs behind nginx (deploy/nginx.conf); see compose.yaml.

FROM python:3.12.16-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# --- ExifTool, pinned and checked: distribution packages are too old --------
FROM base AS exiftool
# exiftool.org keeps only the latest release; SourceForge keeps them all.
# The checksum is the one published on https://exiftool.org/checksums.txt
ARG EXIFTOOL_VERSION=13.60
ARG EXIFTOOL_SHA256=c8e3c42576f46d862e4cd9c192989776e7363931e890c95056bcd6293e83ea36
ADD --checksum=sha256:${EXIFTOOL_SHA256} \
    https://sourceforge.net/projects/exiftool/files/Image-ExifTool-${EXIFTOOL_VERSION}.tar.gz/download \
    /tmp/exiftool.tar.gz
RUN mkdir /opt/exiftool \
 && tar -xzf /tmp/exiftool.tar.gz -C /opt/exiftool --strip-components=1 \
 && rm -rf /opt/exiftool/t /opt/exiftool/html

# --- Python environment, from the lock file ---------------------------------
FROM base AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --locked --no-dev --extra server --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --extra server --no-editable

# --- Runtime ----------------------------------------------------------------
FROM base
# ExifTool is a Perl program; `perl` brings the modules it needs (zlib...).
RUN apt-get update \
 && apt-get install -y --no-install-recommends perl \
 && rm -rf /var/lib/apt/lists/*
COPY --from=exiftool /opt/exiftool /opt/exiftool
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:/opt/exiftool:$PATH" \
    TMPDIR=/tmp
RUN useradd --system --uid 10001 --no-create-home talax
USER talax
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"]
CMD ["talax", "serve", "--host", "0.0.0.0", "--port", "8000"]
