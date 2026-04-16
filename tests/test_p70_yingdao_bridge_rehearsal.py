import argparse

from script import p70_yingdao_bridge_rehearsal as rehearsal


def _args(**kwargs):
    base = {
        "sample": "success",
        "task_id": "",
        "confirm_task_id": "",
        "sku": "A001",
        "delta": 5,
        "old_inventory": 100,
        "target_inventory": 105,
        "environment": "local_poc",
        "force_verify_fail": False,
        "page_profile": "internal_inventory_adjust_v1",
        "page_failure_mode": "",
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


def test_rehearsal_fixed_sample_payloads():
    s = rehearsal._build_payload(_args(sample="success"))
    p = rehearsal._build_payload(_args(sample="page_failure"))
    t = rehearsal._build_payload(_args(sample="timeout"))
    v = rehearsal._build_payload(_args(sample="verify_fail"))
    assert s["task_id"] == "TASK-P70-REHEARSAL-SUCCESS-1"
    assert p["task_id"] == "TASK-P71-REHEARSAL-PFAIL-1"
    assert p["page_failure_mode"] == "element_missing"
    assert t["page_failure_mode"] == "page_timeout"
    assert v["task_id"] == "TASK-P70-REHEARSAL-VFAIL-1"
    assert v["force_verify_fail"] is True


def test_rehearsal_governance_alignment_success():
    out = rehearsal._governance_alignment(
        {"operation_result": "write_adjust_inventory", "verify_passed": True, "failure_layer": ""}
    )
    assert out["sample_bucket"] == "success"
    assert out["p62_view"] == "verify_pass_count"


def test_rehearsal_governance_alignment_timeout_and_verify_fail():
    timeout_out = rehearsal._governance_alignment(
        {"operation_result": "write_adjust_inventory_bridge_timeout", "verify_passed": False, "failure_layer": "bridge_timeout"}
    )
    verify_fail_out = rehearsal._governance_alignment(
        {"operation_result": "write_adjust_inventory_verify_failed", "verify_passed": False, "failure_layer": "verify_failed"}
    )
    assert timeout_out["sample_bucket"] == "timeout_failure"
    assert timeout_out["p62_view"] == "other_failed_confirms"
    assert verify_fail_out["sample_bucket"] == "verify_failure"
    assert verify_fail_out["p62_view"] == "verify_fail_count"


def test_task_id_replay_report_structure(monkeypatch):
    def _fake_bridge_call(base_url: str, payload: dict):  # noqa: ARG001
        return (
            {
                "task_id": payload["task_id"],
                "confirm_task_id": payload["confirm_task_id"],
                "provider_id": payload["provider_id"],
                "capability": payload["capability"],
                "rpa_vendor": "yingdao",
                "operation_result": "write_adjust_inventory_bridge_timeout",
                "verify_passed": False,
                "verify_reason": "bridge_request_timeout",
                "failure_layer": "bridge_timeout",
                "status": "failed",
                "raw_result_path": "",
                "evidence_paths": [],
                "page_url": "http://127.0.0.1:8000/x",
                "page_profile": "internal_inventory_adjust_v1",
                "page_steps": ["open_page"],
                "page_evidence_count": 0,
                "page_failure_code": "page_timeout",
            },
            "",
        )

    monkeypatch.setattr(rehearsal, "_bridge_call", _fake_bridge_call)
    payload = {
        "task_id": "TASK-P71-REPLAY-1",
        "confirm_task_id": "TASK-P71-REPLAY-CFM-1",
        "provider_id": "odoo",
        "capability": "warehouse.adjust_inventory",
        "sku": "A001",
        "delta": 5,
        "old_inventory": 100,
        "target_inventory": 105,
        "environment": "local_poc",
        "force_verify_fail": False,
        "page_profile": "internal_inventory_adjust_v1",
        "page_failure_mode": "page_timeout",
    }
    report = rehearsal.build_task_id_replay_report(task_id="TASK-P71-REPLAY-1", base_url="http://127.0.0.1:17891", payload=payload)
    assert report["mode"] == "task_id_replay"
    assert report["task_id"] == "TASK-P71-REPLAY-1"
    assert "actual" in report
    assert report["actual"]["page_failure_code"] == "page_timeout"
    assert "steps_checklist" in report
    assert "page_failure_code" in report["steps_checklist"]
