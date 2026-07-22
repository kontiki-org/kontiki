from datetime import datetime, timezone

from kontiki.registry.common import normalize_registration_group

INSTANCE_REGISTERED = "registry.instance.registered"
INSTANCE_DEREGISTERED = "registry.instance.deregistered"
INSTANCE_STATUS_CHANGED = "registry.instance.status_changed"
EXCEPTION_RECORDED = "registry.exception.recorded"


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def registered_payload(data):
    payload = {
        "service_name": data["service_name"],
        "instance_id": data["instance_id"],
        "host": data.get("host"),
        "pid": data.get("pid"),
        "service_version": data.get("service_version"),
        "heartbeat_interval": data.get("heartbeat_interval"),
        "group": normalize_registration_group(data.get("group")),
        "timestamp": _utc_now_iso(),
    }
    if data.get("config"):
        payload["config"] = data["config"]
    return payload


def deregistered_payload(service_name, instance_id):
    return {
        "service_name": service_name,
        "instance_id": instance_id,
        "timestamp": _utc_now_iso(),
    }


def status_changed_payload(service_name, instance_id, previous_status, new_status):
    return {
        "service_name": service_name,
        "instance_id": instance_id,
        "previous_status": previous_status,
        "new_status": new_status,
        "timestamp": _utc_now_iso(),
    }


def exception_recorded_payload(exception_data):
    return {
        "service_name": exception_data["service_name"],
        "instance_id": exception_data["instance_id"],
        "exception_type": exception_data.get("exception_type"),
        "message": exception_data.get("message"),
        "context": exception_data.get("context"),
        "timestamp": exception_data.get("timestamp", _utc_now_iso()),
    }
