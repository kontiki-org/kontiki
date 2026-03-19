import pytest
import yaml

from kontiki.configuration.merge import ConfigMergeError, merge


def test_merge_simple(tmp_path):
    config1 = {"a": 1, "b": {"x": 10}}
    config2 = {"b": {"y": 20}, "c": 3}

    file1 = tmp_path / "config1.yml"
    file2 = tmp_path / "config2.yml"

    file1.write_text(yaml.dump(config1), encoding="utf-8")
    file2.write_text(yaml.dump(config2), encoding="utf-8")

    result = merge([str(file1), str(file2)])

    assert result == {"a": 1, "b": {"x": 10, "y": 20}, "c": 3}


def test_merge_conflicting_values_raises(tmp_path):
    config1 = {"a": 1}
    config2 = {"a": 2}

    file1 = tmp_path / "config1.yml"
    file2 = tmp_path / "config2.yml"

    file1.write_text(yaml.dump(config1), encoding="utf-8")
    file2.write_text(yaml.dump(config2), encoding="utf-8")

    with pytest.raises(ConfigMergeError):
        merge([str(file1), str(file2)])


def test_merge_duplicate_same_value_logs_warning(tmp_path, caplog):
    config1 = {"a": 1}
    config2 = {"a": 1}

    file1 = tmp_path / "config1.yml"
    file2 = tmp_path / "config2.yml"

    file1.write_text(yaml.dump(config1), encoding="utf-8")
    file2.write_text(yaml.dump(config2), encoding="utf-8")

    with caplog.at_level("WARNING"):
        result = merge([str(file1), str(file2)])

    assert result == {"a": 1}
    assert any(
        "defined twice with the same value" in rec.getMessage()
        for rec in caplog.records
    )


def test_merge_with_empty_file(tmp_path):
    config1 = {"a": 1}

    file1 = tmp_path / "config1.yml"
    empty_file = tmp_path / "empty.yml"

    file1.write_text(yaml.dump(config1), encoding="utf-8")
    empty_file.write_text("", encoding="utf-8")

    result = merge([str(file1), str(empty_file)])

    assert result == {"a": 1}
