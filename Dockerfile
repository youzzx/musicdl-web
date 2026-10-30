# syntax=docker/dockerfile:1

# MusicDL Web —— musicdl 的网页版外壳
# 构建: docker build -t musicdl-web:1.1 .
# 国内加速: docker build --build-arg DEBIAN_MIRROR=mirrors.tuna.tsinghua.edu.cn \
#                        --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
#                        -t musicdl-web:1.1 .

FROM python:3.12-slim-trixie

# 可选：换成国内镜像源（默认留空，即使用官方源）
ARG DEBIAN_MIRROR=
ARG PIP_INDEX_URL=

RUN set -eux; \
    if [ -n "$DEBIAN_MIRROR" ]; then \
        for f in /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources; do \
            if [ -f "$f" ]; then sed -i "s|https\?://deb\.debian\.org|https://${DEBIAN_MIRROR}|g" "$f"; fi; \
        done; \
    fi

# ffmpeg / flac: 下载后转码与写入音频标签要用
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates ffmpeg flac \
    && rm -rf /var/lib/apt/lists/*

# 独立虚拟环境，避免污染系统 Python
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir \
         ${PIP_INDEX_URL:+--index-url "$PIP_INDEX_URL"} "musicdl==2.14.1"

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MUSICDL_HOST=0.0.0.0 \
    MUSICDL_PORT=8000 \
    MUSICDL_OUTPUT=/app/downloads \
    HOME=/app

WORKDIR /app
COPY app/web /app/web
RUN mkdir -p /app/downloads /app/.cache

VOLUME ["/app/downloads", "/app/.cache"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3).status==200 else 1)"

CMD ["python", "/app/web/server.py"]
