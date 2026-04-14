from app.graph.nodes.execute_action import execute_action


def test_round2_woo_sample_evidence_fields_are_stable(monkeypatch):
    # Keep it unit-level and deterministic (no real HTTP, no DB).
    class _FakeExecutor:
        def query_sku_status(self, sku: str, platform: str):
            _ = (sku, platform)
            return {
                "sku": "A001",
                "product_name": "示例商品 A001",
                "status": "active",
                "inventory": 128,
                "price": 59.9,
                "platform": "woo",
            }

        def get_selected_backend(self):
            return "sandbox_http_client"

        def get_backend_profile(self):
            return "sandbox_http@woo"

        def get_request_adapter_name(self):
            return "woo_request_adapter"

        def get_auth_profile(self):
            return "woo_auth_profile"

        def get_credential_profile(self):
            return "woo_credential_profile"

        def get_production_config_ready(self):
            return "pending"

        def get_dry_run_enabled(self):
            return "false"

        def get_backend_selection_reason(self):
            return "provider_capability_route"

        def get_fallback_enabled(self):
            return "false"

        def get_fallback_applied(self):
            return "false"

        def get_fallback_target(self):
            return "none"

        def get_final_backend(self):
            return "sandbox_http_client"

        def get_dry_run_failure(self):
            return "none"

        def get_mapper_name(self, platform: str):
            _ = platform
            return "woo_mapper"

        def get_provider_profile_name(self, platform: str):
            _ = platform
            return "woo"

    import app.graph.nodes.execute_action as mod

    monkeypatch.setattr(mod, "resolve_execution_mode", lambda intent, m: "api")
    monkeypatch.setattr(mod, "resolve_query_platform", lambda execution_mode, p: "woo")
    monkeypatch.setattr(mod, "get_product_executor", lambda execution_mode: _FakeExecutor())

    state = {
        "intent_code": "product.query_sku_status",
        "slots": {"sku": "A001", "platform": "woo"},
        "task_id": "TASK-P50-R2-MANUAL-WOO-SAMPLE-TEST",
        "raw_text": "查 woo SKU A001 状态",
        "execution_mode": "api",
    }
    out = execute_action(state)

    assert out["provider_id"] == "woo"
    assert out["capability"] == "product.query_sku_status"
    assert out["readiness_status"] != "n/a"
    assert (out["endpoint_profile"] or "").strip()
    assert (out["session_injection_mode"] or "").strip()

