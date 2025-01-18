# SPDX-FileCopyrightText: 2024 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: MIT
.DEFAULT_GOAL := help
LANGPAIRS = de-en  de-es  de-fr  de-zh  en-de  en-es  en-fr  en-zh  es-de  es-en  es-fr  fr-de  fr-en  fr-es  zh-de  zh-en
LANGS=de en es fr zh it sv ar fi nl ja tr
FEW_LANGS=de en

.PHONY: help
help:
	@echo "Welcome to Txt2TxtProvider development. Please use \`make <target>\` where <target> is one of"
	@echo " "
	@echo "  Next commands are only for dev environment with nextcloud-docker-dev!"
	@echo "  They should run from the host you are developing on(with activated venv) and not in the container with Nextcloud!"
	@echo "  "
	@echo "  build-push        build image and upload to ghcr.io"
	@echo "  "
	@echo "  deploy            deploy Txt2TxtProvider to registered 'docker_dev' for Nextcloud Last"
	@echo "  "
	@echo "  run               install Txt2TxtProvider for Nextcloud Last"
	@echo "  "
	@echo "  For development of this example use PyCharm run configurations. Development is always set for last Nextcloud."
	@echo "  First run 'Txt2TxtProvider' and then 'make registerXX', after that you can use/debug/develop it and easy test."
	@echo "  "
	@echo "  register          perform registration of running Txt2TxtProvider into the 'manual_install' deploy daemon."

download-models: $(foreach l1,$(LANGS),$(foreach l2,$(LANGS),models/${l1}-${l2}))

download-a-few-models: $(foreach l1,$(FEW_LANGS),$(foreach l2,$(FEW_LANGS),models/${l1}-${l2}))

models/%:
	GIT_TERMINAL_PROMPT=0 git clone "https://huggingface.co/Helsinki-NLP/opus-mt-$*" "$@" || echo "$* does not exist"

.PHONY: build-pushq
build-push:
	docker login ghcr.io
	docker buildx build --push --platform linux/amd64,linux/arm64/v8 --tag ghcr.io/nextcloud/translate2:latest .

.PHONY: deploy
deploy:
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:unregister translate2 --silent || true
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:deploy translate2 docker_dev \
		--info-xml https://raw.githubusercontent.com/cloud-py-api/translate2/appinfo/info.xml

.PHONY: run
run:
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:unregister translate2 --silent || true
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:register translate2 docker_dev --force-scopes \
		--info-xml https://raw.githubusercontent.com/cloud-py-api/translate2/appinfo/info.xml

.PHONY: register
register:
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:unregister translate2 --silent || true
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:register translate2 manual_install --json-info \
  "{\"appid\":\"translate2\",\"name\":\"Local large language model\",\"daemon_config_name\":\"manual_install\",\"version\":\"2.0.0\",\"secret\":\"12345\",\"host\":\"host.docker.internal\",\"port\":10034,\"scopes\":[\"AI_PROVIDERS\"]}" \
  --force-scopes --wait-finish
