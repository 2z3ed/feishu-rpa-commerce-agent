import importlib.util
import json
from pathlib import Path


def _load_mod():
    script_path = Path("script/p55_woo_release_rehearsal.py").resolve()
    spec = importlib.util.spec_from_file_location("p55_woo_release_rehearsal", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_rehearsal_output_shape_and_checks(monkeypatch):
    mod = _load_mod()

    def _fake_run_json_command(cmd, label):  # noqa: ARG001
        joined = " ".join(cmd)
        if "p54_woo_write_gate_check.py" in joined:
            return (
                {
                    "status": "pass_with_warnings",
                    "gate_status": "pass_with_warnings",
                    "review_hints": [{"rule_name": "unknown_confirms_present", "severity": "warning"}],
                    "review_record_templates": [{"rule_name": "unknown_confirms_present"}],
                },
                "",
            )
        if "--task-id TASK-SUCC" in joined:
            return ({"governance_event_type": "confirm_succeeded", "verify_passed": "True"}, "")
        if "--task-id TASK-REP" in joined:
            return ({"governance_event_type": "confirm_target_already_consumed"}, "")
        if "--task-id TASK-INV" in joined:
            return ({"governance_event_type": "confirm_target_invalid"}, "")
        return ({"governance_distribution": {"confirm_succeeded": 1}}, "")

    monkeypatch.setattr(mod, "_run_json_command", _fake_run_json_command)
    out = mod.run_rehearsal(
        base_url="http://127.0.0.1:8000",
        task_prefix="TASK-",
        limit=80,
        recent_limit=20,
        success_task_id="TASK-SUCC",
        repeat_task_id="TASK-REP",
        invalid_or_unknown_task_id="TASK-INV",
        environment="staging_like",
        gate_skip_tests=True,
    )
    for key in (
        "rehearsal_run_at",
        "environment",
        "covered_checks",
        "key_task_ids",
        "gate_status",
        "review_summary",
        "final_result",
    ):
        assert key in out
    assert out["final_result"] == "passed"
    names = [x["name"] for x in out["covered_checks"]]
    assert names == mod.COVERED_CHECKS
    assert all(bool(x["passed"]) for x in out["covered_checks"])


def test_rehearsal_core_fields_no_missing(monkeypatch):
    mod = _load_mod()

    def _fake_run_json_command(cmd, label):  # noqa: ARG001
        joined = " ".join(cmd)
        if "p54_woo_write_gate_check.py" in joined:
            return ({"status": "fail", "review_hints": [], "review_record_templates": []}, "")
        if "--task-id" in joined:
            return ({}, "replay_err")
        return ({}, "summary_err")

    monkeypatch.setattr(mod, "_run_json_command", _fake_run_json_command)
    out = mod.run_rehearsal(
        base_url="http://127.0.0.1:8000",
        task_prefix="TASK-",
        limit=80,
        recent_limit=20,
        success_task_id="TASK-A",
        repeat_task_id="TASK-B",
        invalid_or_unknown_task_id="TASK-C",
        environment="",
        gate_skip_tests=True,
    )
    assert out["environment"] == ""
    assert isinstance(out["covered_checks"], list)
    assert isinstance(out["key_task_ids"], dict)
    assert isinstance(out["review_summary"], dict)
    assert out["final_result"] == "failed"


def test_main_output_json_same_as_stdout(monkeypatch, tmp_path, capsys):
    mod = _load_mod()
    expected = {
        "rehearsal_run_at": "2026-01-01T00:00:00+08:00",
        "environment": "staging_like",
        "covered_checks": [],
        "key_task_ids": {"success_confirm_task_id": "", "repeat_confirm_task_id": "", "invalid_or_unknown_task_id": ""},
        "gate_status": "pass",
        "review_summary": {},
        "final_result": "passed",
        "artifacts": {},
        "notes": {},
        "links": {},
    }
    monkeypatch.setattr(mod, "run_rehearsal", lambda **kwargs: expected)
    out_path = tmp_path / "rehearsal.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "script/p55_woo_release_rehearsal.py",
            "--success-task-id",
            "TASK-A",
            "--repeat-task-id",
            "TASK-B",
            "--invalid-or-unknown-task-id",
            "TASK-C",
            "--output-json",
            str(out_path),
        ],
    )
    rc = mod.main()
    assert rc == 0
    saved = json.loads(out_path.read_text(encoding="utf-8"))
    assert saved == expected
    printed = json.loads(capsys.readouterr().out)
    assert printed == expected
