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
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


def test_rehearsal_fixed_sample_payloads():
    s = rehearsal._build_payload(_args(sample="success"))
    t = rehearsal._build_payload(_args(sample="timeout"))
    v = rehearsal._build_payload(_args(sample="verify_fail"))
    assert s["task_id"] == "TASK-P70-REHEARSAL-SUCCESS-1"
    assert t["task_id"] == "TASK-P70-REHEARSAL-TIMEOUT-1"
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
