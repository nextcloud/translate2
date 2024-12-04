# SPDX-FileCopyrightText: 2024 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: MIT
FROM nvidia/cuda:12.2.2-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && \
  apt-get install -y software-properties-common && \
  add-apt-repository -y ppa:deadsnakes/ppa && \
  apt-get update && \
  apt-get install -y --no-install-recommends python3.11 python3.11-venv python3-pip vim git && \
  update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
  apt-get -y clean && \
  rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements files
COPY requirements.txt .

# Install requirements
RUN python3 -m pip install --no-cache-dir --no-deps -r requirements.txt

ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute
ENV DEBIAN_FRONTEND dialog

# Copy application files
ADD cs[s]  /app/css
ADD im[g]  /app/img
ADD j[s]   /app/js
ADD l10[n] /app/l10n
ADD li[b]  /app/lib
ADD config.json    /app/config.json
ADD languages.json /app/languages.json

ENTRYPOINT ["python3", "lib/main.py"]

LABEL org.opencontainers.image.source="https://github.com/nextcloud/translate2"
