"""RPA contract, fake runner, and confirm-phase wiring (dev)."""
from __future__ import annotations

import json

from app.core.config import settings
from app.graph.nodes import execute_action
from app.rpa.confirm_update_price import run_confirm_update_price_rpa
from app.rpa.local_fake_runner import LocalFakeRpaRunner
from app.rpa.schema import RpaExecutionInput


def test_rpa_execution_io_models_roundtrip():
    raw = {
        "task_id": "TASK-1",
        "trace_id": "tr-1",
        "intent": "product.update_price",
        "platform": "woo",
        "params": {"sku": "A001", "target_price": 39.9},
        "timeout_s": 60,
        "evidence_dir": "/tmp/ev",
        "verify_mode": "basic",
        "dry_run": False,
    }
    inp = RpaExecutionInput.model_validate(raw)
    d = inp.model_dump()
    assert d["task_id"] == "TASK-1"
    assert d["params"]["sku"] == "A001"


def test_local_fake_runner_writes_evidence_and_succeeds(tmp_path):
    ev = tmp_path / "TASK-X"
    ev.mkdir(parents=True)
    runner = LocalFakeRpaRunner(force_failure=False)
    out = runner.run(
        RpaExecutionInput(
            task_id="TASK-X",
            trace_id="trace",
            intent="product.update_price",
            platform="woo",
            params={"sku": "A001", "target_price": 39.9},
            timeout_s=30,
            evidence_dir=str(ev),
            verify_mode="basic",
            dry_run=False,
        )
    )
    assert out.success is True
    assert out.error_code is None
    assert len(out.evidence_paths) >= 1
    assert (ev / "run_input.json").is_file()
    payload = json.loads((ev / "run_input.json").read_text(encoding="utf-8"))
    assert payload["intent"] == "product.update_price"


def test_local_fake_runner_force_failure(tmp_path):
    ev = tmp_path / "TASK-FAIL"
    ev.mkdir(parents=True)
    runner = LocalFakeRpaRunner(force_failure=True)
    out = runner.run(
        RpaExecutionInput(
            task_id="TASK-FAIL",
            trace_id="t",
            intent="product.update_price",
            platform="woo",
            params={"sku": "A001", "target_price": 1.0},
            timeout_s=30,
            evidence_dir=str(ev),
            verify_mode="none",
            dry_run=False,
        )
    )
    assert out.success is False
    assert out.error_code == "rpa_fake_forced_failure"
    assert any("99_failure" in p for p in out.evidence_paths)


def test_run_confirm_update_price_rpa_success(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RPA_EVIDENCE_BASE_DIR", str(tmp_path / "ev"))
    monkeypatch.setattr(settings, "RPA_FAKE_RUNNER_FORCE_FAILURE", False)
    monkeypatch.setattr(settings, "RPA_UPDATE_PRICE_DRY_RUN", False)
    legacy, err = run_confirm_update_price_rpa(
        confirm_task_id="TASK-RPA-OK",
        trace_id="trace-z",
        sku="A001",
        target_price=39.9,
        platform="woo",
    )
    assert err is None
    assert legacy is not None
    assert legacy["sku"] == "A001"
    assert legacy["status"] == "success"
    assert "_rpa_meta" in legacy
    assert legacy["_rpa_meta"]["evidence_count"] >= 1


def test_run_confirm_update_price_rpa_forced_fail(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RPA_EVIDENCE_BASE_DIR", str(tmp_path / "ev"))
    monkeypatch.setattr(settings, "RPA_FAKE_RUNNER_FORCE_FAILURE", True)
    legacy, err = run_confirm_update_price_rpa(
        confirm_task_id="TASK-RPA-FAIL",
        trace_id="t",
        sku="A001",
        target_price=39.9,
    )
    assert legacy is None
    assert err is not None
    assert err.get("error_code") == "rpa_fake_forced_failure"


def test_execute_action_confirm_merges_rpa_meta(monkeypatch):
    def fake_confirm(_executor, state, slots):
        return {
            "status": "success",
            "sku": "A001",
            "old_price": 10.0,
            "new_price": 20.0,
            "platform": "woo",
            "_rpa_meta": {
                "execution_mode": "rpa",
                "execution_backend": "rpa_local_fake",
                "selected_backend": "rpa_local_fake",
                "final_backend": "rpa_local_fake",
                "rpa_runner": "local_fake",
                "evidence_count": 4,
                "verify_mode": "basic",
            },
        }

    monkeypatch.setattr(
        "app.graph.nodes.execute_action.execute_task_confirmation",
        fake_confirm,
    )
    state = {
        "intent_code": "system.confirm_task",
        "slots": {"task_id": "TASK-ORIG"},
        "task_id": "TASK-CONFIRM",
        "status": "processing",
    }
    out = execute_action.execute_action(state)
    assert out["status"] == "succeeded"
    assert out["execution_mode"] == "rpa"
    assert out["evidence_count"] == 4
    assert out["rpa_runner"] == "local_fake"
    assert out["verify_mode"] == "basic"
    assert out["final_backend"] == "rpa_local_fake"


def test_execute_action_confirm_failure_merges_rpa_meta(monkeypatch):
    def fake_confirm_fail(_executor, state, slots):
        return {
            "error": "LocalFakeRpaRunner: force_failure enabled",
            "_rpa_meta": {
                "execution_mode": "rpa",
                "execution_backend": "rpa_local_fake",
                "selected_backend": "rpa_local_fake",
                "final_backend": "rpa_local_fake",
                "rpa_runner": "local_fake",
                "evidence_count": 3,
                "verify_mode": "basic",
                "platform": "woo",
            },
        }

    monkeypatch.setattr(
        "app.graph.nodes.execute_action.execute_task_confirmation",
        fake_confirm_fail,
    )
    state = {
        "intent_code": "system.confirm_task",
        "slots": {"task_id": "TASK-ORIG"},
        "task_id": "TASK-CONFIRM",
        "status": "processing",
    }
    out = execute_action.execute_action(state)
    assert out["status"] == "failed"
    assert out["execution_mode"] == "rpa"
    assert out["execution_backend"] == "rpa_local_fake"
    assert out["evidence_count"] == 3
    assert out["rpa_runner"] == "local_fake"
    assert out["verify_mode"] == "basic"
    assert out["platform"] == "woo"
    assert out["final_backend"] == "rpa_local_fake"


def test_run_confirm_update_price_rpa_failure_includes_meta(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "RPA_EVIDENCE_BASE_DIR", str(tmp_path / "ev"))
    monkeypatch.setattr(settings, "RPA_FAKE_RUNNER_FORCE_FAILURE", True)
    legacy, err = run_confirm_update_price_rpa(
        confirm_task_id="TASK-META-FAIL",
        trace_id="t",
        sku="A001",
        target_price=39.9,
    )
    assert legacy is None and err is not None
    assert "_rpa_meta" in err
    assert err["_rpa_meta"]["execution_mode"] == "rpa"
    assert err["_rpa_meta"]["evidence_count"] >= 1
    assert err["_rpa_meta"]["platform"] == "woo"
