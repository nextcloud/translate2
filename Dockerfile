# SPDX-FileCopyrightText: 2024 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
FROM nvidia/cuda:12.2.2-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && \
  apt-get install -y software-properties-common && \
  add-apt-repository -y ppa:deadsnakes/ppa && \
  apt-get update && \
  apt-get install -y --no-install-recommends python3.11 python3.11-venv python3-pip vim git curl && \
  update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
  apt-get -y clean && \
  rm -rf /var/lib/apt/lists/*

# Download and install FRP client into /usr/local/bin.
RUN set -ex; \
    ARCH=$(uname -m); \
    if [ "$ARCH" = "aarch64" ]; then \
      FRP_URL="https://raw.githubusercontent.com/nextcloud/HaRP/main/exapps_dev/frp_0.61.1_linux_arm64.tar.gz"; \
    else \
      FRP_URL="https://raw.githubusercontent.com/nextcloud/HaRP/main/exapps_dev/frp_0.61.1_linux_amd64.tar.gz"; \
    fi; \
    echo "Downloading FRP client from $FRP_URL"; \
    curl -L "$FRP_URL" -o /tmp/frp.tar.gz; \
    tar -C /tmp -xzf /tmp/frp.tar.gz; \
    mv /tmp/frp_0.61.1_linux_* /tmp/frp; \
    cp /tmp/frp/frpc /usr/local/bin/frpc; \
    chmod +x /usr/local/bin/frpc; \
    rm -rf /tmp/frp /tmp/frp.tar.gz

# Set working directory
WORKDIR /app

# Copy requirements files
COPY requirements.txt .

# Install requirements
RUN python3 -m pip install --no-cache-dir --no-deps -r requirements.txt

ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute
ENV DEBIAN_FRONTEND dialog

COPY healthcheck.sh /
COPY --chmod=775 start.sh /

# Copy application files
ADD cs[s]  /app/css
ADD im[g]  /app/img
ADD j[s]   /app/js
ADD l10[n] /app/l10n
ADD li[b]  /app/lib
ADD config.json    /app/config.json
ADD languages.json /app/languages.json

ENTRYPOINT ["/start.sh", "python3", "lib/main.py"]
HEALTHCHECK --interval=2s --timeout=2s --retries=300 CMD /healthcheck.sh

LABEL org.opencontainers.image.source="https://github.com/nextcloud/translate2"
