import re
from pathlib import Path

from behave import then

SHORT_INSTANCE_ID_RE = re.compile(r"[0-9a-f]{12}")
IDENTITY_IN_LOG = re.compile(r" - ([0-9a-f]{12}) - ")


def _short_instance_id_from_service_log(context):
    manager = getattr(context, "service_name_manager", None)
    assert manager is not None, "No service process manager on context"
    content = manager.log_file_path.read_text(encoding="utf-8")
    match = IDENTITY_IN_LOG.search(content)
    assert match, f"No short_instance_id column in {manager.log_file_path}"
    return match.group(1)


@then('the log file "{path_template}" exists')
def step_log_file_exists(context, path_template):
    if "[SHORT_INSTANCE_ID]" in path_template:
        short_id = _short_instance_id_from_service_log(context)
        path = Path(path_template.replace("[SHORT_INSTANCE_ID]", short_id))
        assert path.is_file(), (
            f"Expected log file {path} to exist " f"(short_instance_id={short_id})"
        )
        return

    path = Path(path_template)
    assert path.is_file(), f"Expected log file {path} to exist"
