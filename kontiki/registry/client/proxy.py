from kontiki.messaging.publisher.rpc import RpcProxy

# -----------------------------------------------------------------------------


class ServiceRegistryProxy(RpcProxy):
    def __init__(self, messenger):
        super().__init__(messenger, service_name="ServiceRegistry")
