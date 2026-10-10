# kontiki-registry

The registry records the fleet: heartbeats, instance state, and activity. Other services register with it. `GET /live/ServiceRegistry` answers once its HTTP server is up.

## Configure and run

The process uses the same `kontiki.*` keys as any service (`amqp`, `http`). `activity_tracker` sets how long event and exception records are kept. Field reference: [configuration](../../docs/configuration.md#registry-server-only).

```yaml
kontiki:
  amqp:
    url: amqp://guest:guest@localhost/
  http:
    address: 0.0.0.0
    port: 8082
```

`examples/common.yaml` is the broker. `examples/registry/config.yaml` sets HTTP on port 8082.

```bash
docker run --rm \
  -v "$PWD/examples:/examples:ro" \
  ghcr.io/kontiki-org/kontiki-registry:2.3.2 \
  --config /examples/registry/config.yaml \
  --config /examples/common.yaml
```

From a checkout:

```bash
poetry run kontiki_registry \
  --config examples/registry/config.yaml \
  --config examples/common.yaml
```
