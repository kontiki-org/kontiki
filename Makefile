.PHONY: \
	install test cov fmt lint check clean \
	run-amqp down-amqp \
	run-rpc-service run-rpc-example \
	run-session-service run-session-example \
	run-simple-events-service run-simple-events-example \
	run-serialization-service run-serialization-example \
	run-registry run-registry-service run-registry-client \
	run-task-service

PY ?= poetry run python

install:
	$(PY) -m pip install -U pip setuptools wheel
	poetry install || true

poetry-update:
	poetry update

test:
	$(PY) -m pytest -q

fmt:
	$(PY) -m isort .
	$(PY) -m black .

lint:
	$(PY) -m flake8 kontiki tests

check: fmt lint

clean:
	rm -rf .venv .mypy_cache .pytest_cache .ruff_cache .coverage dist build

commit: test fmt lint
	@git status
	@echo "Committing with message: $(MSG)"
	git commit -am "$(MSG)"


# INTEGRATION TESTS
# -----------------------------------------------------------------------------

run-test-service: run-amqp
	@echo "Starting TestService..."
	$(PY) -m kontiki.runner.__main__ tests.integration.service.TestService --config tests/integration/config.yaml

integration-test:
	$(PY) -m behave tests/integration --stop

# EXAMPLES
# -----------------------------------------------------------------------------
# RPC Service
# -----------------------------------------------------------------------------
run-rpc-service: run-amqp
	@echo "Starting RpcService..."
	$(PY) -m kontiki.runner.__main__ examples.rpc.service.RpcService --config examples/common.yaml --config examples/rpc/rpc_service.yaml

run-rpc-example:
	@echo "Running RPC example..."
	$(PY) -m examples.rpc.rpc_example

# -----------------------------------------------------------------------------
# Task Service
# -----------------------------------------------------------------------------
run-task-service: run-amqp
	@echo "Starting TaskService..."
	$(PY) -m kontiki.runner.__main__ examples.task.service.TaskService --config examples/common.yaml

# -----------------------------------------------------------------------------
# Session Service
# -----------------------------------------------------------------------------
run-session-service: run-amqp
	@echo "Starting SessionService..."
	$(PY) -m kontiki.runner.__main__ examples.events.session.service.SessionService --config examples/common.yaml

run-session-example:
	@echo "Running session example..."
	$(PY) -m examples.events.session.session_example

# -----------------------------------------------------------------------------
# Simple events
# -----------------------------------------------------------------------------
run-simple-events-service: run-amqp
	@echo "Starting SimpleEventService..."
	$(PY) -m kontiki.runner.__main__ examples.events.simple.service.SimpleEventService --config examples/common.yaml --config examples/events/simple/event_service.yaml

run-simple-events-example:
	@echo "Running simple events example..."
	$(PY) -m examples.events.simple.simple_example

# -----------------------------------------------------------------------------
# Broadcast events
# -----------------------------------------------------------------------------
# Note: To be launched twice to observe per-instance vs per-service behaviour.
run-broadcast-service: run-amqp
	@echo "Starting BroadcastService..."
	$(PY) -m kontiki.runner.__main__ examples.events.broadcast.service.BroadcastService --config examples/common.yaml

run-broadcast-example:
	@echo "Running broadcast example..."
	$(PY) -m examples.events.broadcast.broadcast_example

# -----------------------------------------------------------------------------
# Serialization events
# -----------------------------------------------------------------------------
run-serialization-service: run-amqp
	@echo "Starting SerializationService..."
	$(PY) -m kontiki.runner.__main__ examples.events.serialization.service.SerializationService --config examples/common.yaml

run-serialization-example:
	@echo "Running serialization example..."
	$(PY) -m examples.events.serialization.serialization_example

# -----------------------------------------------------------------------------
# Registry
# -----------------------------------------------------------------------------
run-registry: run-amqp
	@echo "Starting Kontiki registry..."
	poetry run kontiki_registry --config examples/registry/config.yaml --config examples/common.yaml

run-registry-service: run-amqp
	@echo "Starting RegistryExampleService..."
	$(PY) -m kontiki.runner.__main__ examples.registry.service.RegistryExampleService --config examples/common.yaml

run-registry-client:
	@echo "Running registry example client..."
	$(PY) -m examples.registry.client

# -----------------------------------------------------------------------------
# Heartbeat (Degraded state)
# Run also run-registry to start the registry to look at the degraded state of the service.
# -----------------------------------------------------------------------------
run-heartbeat-service: run-amqp
	@echo "Starting HeartbeatExampleService..."
	$(PY) -m kontiki.runner.__main__ examples.heartbeat.service.HeartbeatExampleService --config examples/common.yaml --config examples/heartbeat/heartbeat_example.yaml

run-heartbeat-example:
	@echo "Running heartbeat example..."
	$(PY) -m examples.heartbeat.heartbeat_example

# -----------------------------------------------------------------------------
# HTTP (simple)
# -----------------------------------------------------------------------------
run-http-service: run-amqp
	@echo "Starting SimpleHttpService..."
	$(PY) -m kontiki.runner.__main__ examples.http.simple.service.SimpleHttpService --config examples/common.yaml --config examples/http/simple/http_example.yaml

run-http-example:
	@echo "Calling SimpleHttpService endpoints..."
	@echo "GET /health"
	curl -s http://localhost:8080/health | jq .
	@echo ""
	@echo "GET /ping (path from config)"
	curl -s http://localhost:8080/ping | jq .
	@echo ""
	@echo "POST /echo"
	curl -s -X POST http://localhost:8080/echo -H "Content-Type: application/json" -d '{"message": "Hello from HTTP example"}' | jq .
	@echo ""
	@echo "GET /fail (should return HTTP 400)"
	curl -s http://localhost:8080/fail | jq .
	curl -s -o /dev/null -w "HTTP status: %{http_code}\n" http://localhost:8080/fail

# -----------------------------------------------------------------------------
# AMQP
# -----------------------------------------------------------------------------
run-amqp:
	docker compose -f docker-compose.dev.yaml up -d --wait --wait-timeout 60 rabbitmq

down-amqp:
	docker compose -f docker-compose.dev.yaml down

