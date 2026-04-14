import importlib.util
import json
from pathlib import Path


def _load_gate_module():
    script_path = Path("script/p54_woo_write_gate_check.py").resolve()
    spec = importlib.util.spec_from_file_location("p54_woo_write_gate_check", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_gate_pass_with_warnings(monkeypatch):
    mod = _load_gate_module()

    def _fake_run_command(cmd):
        text = " ".join(cmd)
        if text.startswith("pytest -q"):
            return 0, "... 3 passed ...", ""
        if "--task-id" in cmd:
            task_id = cmd[-1]
            return (
                0,
                (
                    '{"confirm_task_id":"%s","target_task_id":"TASK-U1","original_update_task_id":"TASK-U1",'
                    '"operation_result":"write_update_price","verify_passed":"True","verify_reason":"ok",'
                    '"failure_layer":"","governance_event_type":"confirm_succeeded","source_mode":"new_schema","unknown_reason":""}'
                    % task_id
                ),
                "",
            )
        return (
            0,
            (
                '{"total_confirm_attempts":10,"successful_confirms":7,"blocked_repeat_confirms":0,'
                '"invalid_target_confirms":1,"other_failed_confirms":0,"unknown_confirms":1,'
                '"governance_distribution":{"confirm_succeeded":7,"confirm_target_invalid":1,"unknown":1},'
                '"source_mode_distribution":{"new_schema":7,"legacy_compatible":2,"unknown":1},'
                '"unknown_reason_distribution":{"summary_message_not_classifiable":1},'
                '"recent_governance_events":['
                '{"task_id":"TASK-C9","confirm_task_id":"TASK-C9","governance_event_type":"unknown"},'
                '{"task_id":"TASK-C8","confirm_task_id":"TASK-C8","governance_event_type":"confirm_target_invalid"},'
                '{"task_id":"TASK-C7","confirm_task_id":"TASK-C7","governance_event_type":"confirm_succeeded"}'
                ']}'
            ),
            "",
        )

    monkeypatch.setattr(mod, "_run_command", _fake_run_command)
    out = mod.run_gate_check(
        base_url="http://127.0.0.1:8000",
        limit=80,
        task_prefix="TASK-",
        recent_limit=20,
        replay_task_ids=["TASK-C1"],
        run_tests=True,
    )
    assert out["status"] == "pass_with_warnings"
    assert out["gate_status"] == out["status"]
    assert isinstance(out.get("gate_run_at"), str) and out["gate_run_at"]
    assert out["blocking_failures"] == []
    assert "tests/test_p53_woo_write_governance_summary.py" in out["checked_tests"]
    assert "script/p53_woo_write_governance_summary.py" in out["checked_scripts"]
    assert isinstance(out.get("sample_task_ids"), list)
    assert any("blocked_repeat_confirms_eq_0" in w for w in out["warnings"])
    assert any("invalid_target_confirms_present" in w for w in out["warnings"])
    assert any("unknown_confirms_present" in w for w in out["warnings"])
    assert isinstance(out.get("review_hints"), list)
    hint_rules = {h["rule_name"] for h in out["review_hints"]}
    assert "unknown_confirms_present" in hint_rules
    assert "blocked_repeat_confirms_eq_0" in hint_rules
    assert "invalid_target_confirms_present" in hint_rules
    for h in out["review_hints"]:
        assert h["recommended_entry"] in {"p53_replay_task_id", "tasks_detail", "steps_action_executed"}
        assert h["recommended_action"] in {"block", "review", "allow"}
        assert "recommended_task_ids" in h
    templates = out.get("review_record_templates")
    assert isinstance(templates, list) and len(templates) >= 1
    t = templates[0]
    for key in (
        "gate_run_at",
        "gate_status",
        "rule_name",
        "severity",
        "recommended_action",
        "recommended_entry",
        "reviewed_task_ids",
        "replay_result_summary",
        "final_decision",
        "reviewer",
        "note",
    ):
        assert key in t
    assert t["gate_run_at"] == out["gate_run_at"]
    assert t["gate_status"] == out["gate_status"]


def test_gate_blocking_failure_when_other_failed(monkeypatch):
    mod = _load_gate_module()

    def _fake_run_command(cmd):
        text = " ".join(cmd)
        if text.startswith("pytest -q"):
            return 0, "ok", ""
        if "--task-id" in cmd:
            task_id = cmd[-1]
            return (
                0,
                (
                    '{"confirm_task_id":"%s","target_task_id":"TASK-U1","original_update_task_id":"TASK-U1",'
                    '"operation_result":"confirm_blocked_noop","verify_passed":"False","verify_reason":"x",'
                    '"failure_layer":"confirm_target_invalid","governance_event_type":"confirm_target_invalid",'
                    '"source_mode":"legacy_compatible","unknown_reason":""}'
                    % task_id
                ),
                "",
            )
        return (
            0,
            (
                '{"total_confirm_attempts":5,"successful_confirms":2,"blocked_repeat_confirms":1,'
                '"invalid_target_confirms":1,"other_failed_confirms":1,"unknown_confirms":0,'
                '"governance_distribution":{"other_failed":1},'
                '"source_mode_distribution":{"new_schema":2},'
                '"unknown_reason_distribution":{},'
                '"recent_governance_events":['
                '{"task_id":"TASK-C2","confirm_task_id":"TASK-C2","governance_event_type":"other_failed"}'
                ']}'
            ),
            "",
        )

    monkeypatch.setattr(mod, "_run_command", _fake_run_command)
    out = mod.run_gate_check(
        base_url="http://127.0.0.1:8000",
        limit=80,
        task_prefix="TASK-",
        recent_limit=20,
        replay_task_ids=["TASK-C2"],
        run_tests=True,
    )
    assert out["status"] == "fail"
    assert out["gate_status"] == "fail"
    assert any("other_failed_confirms_gt_0" in x for x in out["blocking_failures"])
    hint = next(h for h in out["review_hints"] if h["rule_name"] == "other_failed_confirms_gt_0")
    assert hint["recommended_action"] == "block"
    assert hint["recommended_entry"] == "p53_replay_task_id"
    assert hint["recommended_task_ids"] == ["TASK-C2"]


def test_gate_blocking_failure_when_unknown_ratio_high(monkeypatch):
    mod = _load_gate_module()

    def _fake_run_command(cmd):
        text = " ".join(cmd)
        if text.startswith("pytest -q"):
            return 0, "ok", ""
        if "--task-id" in cmd:
            task_id = cmd[-1]
            return (
                0,
                (
                    '{"confirm_task_id":"%s","target_task_id":"","original_update_task_id":"",'
                    '"operation_result":"","verify_passed":"","verify_reason":"",'
                    '"failure_layer":"","governance_event_type":"unknown","source_mode":"unknown",'
                    '"unknown_reason":"summary_message_not_classifiable"}'
                    % task_id
                ),
                "",
            )
        return (
            0,
            (
                '{"total_confirm_attempts":10,"successful_confirms":4,"blocked_repeat_confirms":2,'
                '"invalid_target_confirms":1,"other_failed_confirms":0,"unknown_confirms":3,'
                '"governance_distribution":{"unknown":3},'
                '"source_mode_distribution":{"unknown":3},'
                '"unknown_reason_distribution":{"summary_message_not_classifiable":3},'
                '"recent_governance_events":['
                '{"task_id":"TASK-C3","confirm_task_id":"TASK-C3","governance_event_type":"unknown"},'
                '{"task_id":"TASK-C4","confirm_task_id":"TASK-C4","governance_event_type":"unknown"}'
                ']}'
            ),
            "",
        )

    monkeypatch.setattr(mod, "_run_command", _fake_run_command)
    out = mod.run_gate_check(
        base_url="http://127.0.0.1:8000",
        limit=80,
        task_prefix="TASK-",
        recent_limit=20,
        replay_task_ids=["TASK-C3"],
        run_tests=True,
    )
    assert out["status"] == "fail"
    assert any("unknown_ratio_gt_threshold" in x for x in out["blocking_failures"])
    hint = next(h for h in out["review_hints"] if h["rule_name"] == "unknown_ratio_gt_threshold")
    assert hint["recommended_action"] == "block"
    assert hint["recommended_entry"] == "p53_replay_task_id"
    assert hint["recommended_task_ids"] == ["TASK-C3", "TASK-C4"]


def test_review_record_template_link_keys(monkeypatch):
    mod = _load_gate_module()

    def _fake_run_command(cmd):
        text = " ".join(cmd)
        if text.startswith("pytest -q"):
            return 0, "ok", ""
        if "--task-id" in cmd:
            task_id = cmd[-1]
            return (
                0,
                (
                    '{"confirm_task_id":"%s","target_task_id":"","original_update_task_id":"",'
                    '"operation_result":"","verify_passed":"","verify_reason":"",'
                    '"failure_layer":"","governance_event_type":"unknown","source_mode":"unknown",'
                    '"unknown_reason":"summary_message_not_classifiable"}'
                    % task_id
                ),
                "",
            )
        return (
            0,
            (
                '{"total_confirm_attempts":10,"successful_confirms":8,"blocked_repeat_confirms":1,'
                '"invalid_target_confirms":0,"other_failed_confirms":0,"unknown_confirms":1,'
                '"governance_distribution":{"unknown":1},'
                '"source_mode_distribution":{"unknown":1},'
                '"unknown_reason_distribution":{"summary_message_not_classifiable":1},'
                '"recent_governance_events":['
                '{"task_id":"TASK-LINK-1","confirm_task_id":"TASK-LINK-1","governance_event_type":"unknown"}'
                ']}'
            ),
            "",
        )

    monkeypatch.setattr(mod, "_run_command", _fake_run_command)
    out = mod.run_gate_check(
        base_url="http://127.0.0.1:8000",
        limit=80,
        task_prefix="TASK-",
        recent_limit=20,
        replay_task_ids=["TASK-LINK-1"],
        run_tests=True,
    )
    hint = next(h for h in out["review_hints"] if h["rule_name"] == "unknown_confirms_present")
    template = next(t for t in out["review_record_templates"] if t["rule_name"] == "unknown_confirms_present")
    assert template["gate_run_at"] == out["gate_run_at"]
    assert template["rule_name"] == hint["rule_name"]
    assert template["reviewed_task_ids"] == hint["recommended_task_ids"]


def test_output_json_equals_stdout_structure(monkeypatch, tmp_path):
    mod = _load_gate_module()
    fake_out = {
        "status": "pass",
        "gate_run_at": "2026-01-01T00:00:00+08:00",
        "gate_status": "pass",
        "blocking_failures": [],
        "warnings": [],
        "review_hints": [],
        "checked_tests": [],
        "checked_scripts": ["script/p53_woo_write_governance_summary.py"],
        "sample_task_ids": [],
        "review_record_templates": [
            {
                "gate_run_at": "2026-01-01T00:00:00+08:00",
                "gate_status": "pass",
                "rule_name": "",
                "severity": "",
                "recommended_action": "",
                "recommended_entry": "",
                "reviewed_task_ids": [],
                "replay_result_summary": "",
                "final_decision": "",
                "reviewer": "",
                "note": "",
            }
        ],
        "thresholds": {},
        "checks": {},
    }

    monkeypatch.setattr(mod, "run_gate_check", lambda **kwargs: fake_out)
    out_path = tmp_path / "gate.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "script/p54_woo_write_gate_check.py",
            "--output-json",
            str(out_path),
            "--skip-tests",
        ],
    )
    rc = mod.main()
    assert rc == 0
    saved = json.loads(out_path.read_text(encoding="utf-8"))
    assert saved == fake_out
