IMAGE = shad-rc
REGISTRY = cr.yandex/$(REGISTRY_ID)
REMOTE = $(REGISTRY)/$(IMAGE)

test-lint:
	flake8 neludim

test-key:
	pytest -vv -s -k $(KEY) neludim

image:
	docker build -t $(IMAGE) .

push:
	docker tag $(IMAGE) $(REMOTE)
	docker push $(REMOTE)

deploy-bot:
	yc serverless container revision deploy \
		--container-name bot \
		--image $(REGISTRY)/$(IMAGE):latest \
		--args bot-webhook \
		--cores 1 \
		--memory 256MB \
		--concurrency 16 \
		--execution-timeout 30s \
		--environment BOT_TOKEN=$(BOT_TOKEN) \
		--environment AWS_KEY_ID=$(AWS_KEY_ID) \
		--environment AWS_KEY=$(AWS_KEY) \
		--environment DYNAMO_ENDPOINT=$(DYNAMO_ENDPOINT) \
		--environment ADMIN_USER_ID=$(ADMIN_USER_ID) \
		--environment CHAT_ID=$(CHAT_ID) \
		--service-account-id $(SERVICE_ACCOUNT_ID) \
		--folder-name shad-rc

deploy-trigger:
	yc serverless container revision deploy \
		--container-name trigger \
		--image $(REGISTRY)/$(IMAGE):latest \
		--args trigger-webhook \
		--cores 1 \
		--memory 256MB \
		--concurrency 16 \
		--execution-timeout 60s \
		--environment BOT_TOKEN=$(BOT_TOKEN) \
		--environment AWS_KEY_ID=$(AWS_KEY_ID) \
		--environment AWS_KEY=$(AWS_KEY) \
		--environment DYNAMO_ENDPOINT=$(DYNAMO_ENDPOINT) \
		--environment ADMIN_USER_ID=$(ADMIN_USER_ID) \
		--environment CHAT_ID=$(CHAT_ID) \
		--service-account-id $(SERVICE_ACCOUNT_ID) \
		--folder-name shad-rc

log-follow:
	yc log read default \
		--filter 'json_payload.source = "user"' \
		--follow \
		--folder-name shad-rc

log-1000:
	yc log read default \
		--filter 'json_payload.source = "user"' \
		--limit 1000 \
		--since 2020-01-01T00:00:00Z \
		--until 2030-01-01T00:00:00Z \
		--folder-name shad-rc
