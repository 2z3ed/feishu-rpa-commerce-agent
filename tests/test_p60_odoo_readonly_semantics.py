from app.graph.nodes.execute_action import execute_action


def test_odoo_inventory_default_execution_mode_is_api():
    state = {
        "intent_code": "warehouse.query_inventory",
        "slots": {"sku": "A001", "platform": "odoo"},
        # no execution_mode provided
        "status": "processing",
    }
    out = execute_action(state)
    assert out["status"] == "succeeded"
    assert out["execution_mode"] == "api"


def test_odoo_inventory_result_summary_template_stable():
    state = {
        "intent_code": "warehouse.query_inventory",
        "slots": {"sku": "A001", "platform": "odoo"},
        "status": "processing",
    }
    out = execute_action(state)
    summary = out.get("result_summary") or ""
    # fixed template anchors
    for k in (
        "SKU: A001",
        "商品：",
        "库存：",
        "状态：",
        "平台：odoo",
        "provider_id：odoo",
        "capability：warehouse.query_inventory",
        "readiness：ready",
    ):
        assert k in summary

