import base64
import json
from datetime import date, datetime, time
from uuid import UUID

from kontiki.messaging.rpc import RpcErrorType, RpcReturn


class Serializer:
    """JSON-only serializer for Kontiki 2.0+."""

    def __init__(self, config):
        self.config = config

    def _default_encoder(self, obj):
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, bytes):
            return {"__bytes__": True, "data": base64.b64encode(obj).decode("ascii")}
        if isinstance(obj, RpcReturn):
            return {
                "__rpcreturn__": True,
                "success": obj.success,
                "result": obj.result,
                "message": obj.message,
                "error_type": obj.error_type.name,
                "error_code": obj.error_code,
            }
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        if hasattr(obj, "dict"):
            return obj.dict()
        try:
            return dict(obj)
        except TypeError:
            raise TypeError(f"Cannot serialize {type(obj).__name__} to JSON")

    def _object_hook(self, dct):
        if dct.get("__rpcreturn__") is True:
            error_type = (
                RpcErrorType[dct["error_type"]]
                if "error_type" in dct
                else RpcErrorType.NONE
            )
            return RpcReturn(
                success=dct["success"],
                result=dct.get("result"),
                message=dct.get("message"),
                error_type=error_type,
                error_code=dct.get("error_code"),
            )
        if dct.get("__bytes__") is True:
            return base64.b64decode(dct["data"])
        return dct

    def dumps(self, obj):
        return json.dumps(
            obj, default=self._default_encoder, ensure_ascii=False
        ).encode("utf-8")

    def loads(self, data):
        return json.loads(data.decode("utf-8"), object_hook=self._object_hook)
