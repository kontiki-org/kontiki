from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional


class RpcErrorType(Enum):
    NONE = auto()
    CLIENT = auto()
    SERVER = auto()


@dataclass
class RpcReturn:
    success: bool
    result: Optional[Any] = None
    message: Optional[str] = None
    error_type: RpcErrorType = RpcErrorType.NONE
    error_code: Optional[str] = None
