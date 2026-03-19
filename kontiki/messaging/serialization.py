import json
import pickle

from kontiki.configuration.parameter import get_kontiki_parameter
from kontiki.messaging.rpc import RpcErrorType, RpcReturn
from kontiki.utils import log

# -----------------------------------------------------------------------------

DEFAULT_SERIALIZATION = "pickle"
SUPPORTED_SERIALIZATIONS = ["pickle", "json"]

# -----------------------------------------------------------------------------


class Serializer:
    def __init__(self, config, serialization=DEFAULT_SERIALIZATION):
        self.serialization = get_kontiki_parameter(
            config, "amqp.serialization", serialization
        )
        if self.serialization not in SUPPORTED_SERIALIZATIONS:
            msg = f"{self.serialization} serializer not supported."
            log.error(msg)
            raise RuntimeError(msg)

    def _rpcreturn_object_hook(self, obj):
        if obj.get("__rpcreturn__") is True:
            error_type_str = obj.get("error_type", "NONE")
            error_type = (
                RpcErrorType[error_type_str]
                if error_type_str in RpcErrorType.__members__
                else RpcErrorType.NONE
            )
            return RpcReturn(
                success=obj.get("success", False),
                result=obj.get("result"),
                message=obj.get("message"),
                error_type=error_type,
            )
        return obj

    def _default_encoder(self, obj):
        if isinstance(obj, RpcReturn):
            log.debug(
                "Encode RpcReturn object: %s",
                obj.result if obj.success else obj.message,
            )
            return {
                "__rpcreturn__": True,
                "success": obj.success,
                "result": obj.result,
                "message": obj.message,
                "error_type": obj.error_type.name,
            }
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    def loads(self, message_body):
        if self.serialization == "json":
            return json.loads(
                message_body.decode(), object_hook=self._rpcreturn_object_hook
            )

        return pickle.loads(message_body)

    def dumps(self, message_body):
        if self.serialization == "json":
            return json.dumps(message_body, default=self._default_encoder).encode()

        return pickle.dumps(message_body)
