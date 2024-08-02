#!/usr/bin/env sh

echo "Building docker image for translate2:${1:-latest}"

docker build -t ghcr.io/nextcloud/translate2:latest .
