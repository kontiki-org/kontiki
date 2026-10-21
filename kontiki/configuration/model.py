from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from kontiki.messaging.common import AMQP_DEFAULT_URL

# -----------------------------------------------------------------------------


class RpcConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    timeout: int | float = 10


class TlsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool = False
    ca_cert: str | None = None
    client_cert: str | None = None
    client_key: str | None = None

    @model_validator(mode="after")
    def certificate_when_enabled(self):
        if self.enabled and not self.ca_cert:
            raise ValueError(
                "kontiki.amqp.tls.ca_cert is required when TLS is enabled."
            )
        return self


class AmqpConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    url: str = AMQP_DEFAULT_URL
    disable: bool = False
    required: bool = True
    rpc: RpcConfig = Field(default_factory=RpcConfig)
    max_pending_messages: int = 10
    max_attempts: int = Field(default=3, ge=1)
    tls: TlsConfig = Field(default_factory=TlsConfig)


class ShutdownConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    grace_seconds: int | float = 25


class RegistrationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    disable: bool = False
    delay: int | float = 2
    group: str = "business"
    report_uncaught_exceptions: bool = True


class HeartbeatConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    interval: int | float = 60


class HttpDocumentationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool = True
    path_template: str = "/api/{version}/docs"
    title: str | None = None
    description: str | None = None


class HttpConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    disable: bool = False
    address: str = "0.0.0.0"
    port: int = 8080
    documentation: HttpDocumentationConfig = Field(
        default_factory=HttpDocumentationConfig
    )


class KontikiConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    service_name: str | None = None
    peers: dict[str, str] = Field(default_factory=dict)
    amqp: AmqpConfig = Field(default_factory=AmqpConfig)
    shutdown: ShutdownConfig = Field(default_factory=ShutdownConfig)
    registration: RegistrationConfig = Field(default_factory=RegistrationConfig)
    heartbeat: HeartbeatConfig = Field(default_factory=HeartbeatConfig)
    http: HttpConfig = Field(default_factory=HttpConfig)

    @field_validator("service_name")
    @classmethod
    def service_name_non_empty(cls, value):
        if value is not None and not value:
            raise ValueError("kontiki.service_name must be a non-empty string")
        return value

    @field_validator("peers")
    @classmethod
    def peer_targets_non_empty(cls, peers):
        for name, target in peers.items():
            if not name or not target:
                raise ValueError(
                    f"kontiki.peers.{name} must be a non-empty string, got {target!r}"
                )
        return peers

    @model_validator(mode="after")
    def amqp_disable_conflicts(self):
        if not self.amqp.disable:
            return self
        # Defaults are not conflicts. Only keys written in the file count.
        if "required" in self.amqp.model_fields_set and self.amqp.required:
            raise ValueError(
                "kontiki.amqp.disable and kontiki.amqp.required cannot both be true."
            )
        if (
            "disable" in self.registration.model_fields_set
            and self.registration.disable is False
        ):
            raise ValueError(
                "kontiki.amqp.disable cannot be combined with "
                "kontiki.registration.disable: false."
            )
        return self
