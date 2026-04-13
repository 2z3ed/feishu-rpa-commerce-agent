from app.clients.product_provider_profile import list_provider_ids
from app.clients.product_provider_readiness import check_platform_provider_readiness
from app.graph.nodes.execute_action import execute_action


def test_provider_registry_includes_multi_platform_connectors():
    ids = list_provider_ids()
    assert "woo" in ids
    assert "odoo" in ids
    assert "chatwoot" in ids


def test_provider_readiness_chatwoot_ok():
    result = check_platform_provider_readiness("chatwoot", capability="customer.list_recent_conversations")
    assert result.ready is True
    assert result.provider_name == "chatwoot"


def test_odoo_inventory_route_succeeds_in_task_chain():
    state = {
        "intent_code": "warehouse.query_inventory",
        "slots": {"sku": "A001", "platform": "odoo"},
        "execution_mode": "api",
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert result["platform"] == "odoo"
    assert result["provider_id"] == "odoo"
    assert "库存：" in result["result_summary"]


def test_chatwoot_recent_conversations_route_succeeds_in_task_chain():
    state = {
        "intent_code": "customer.list_recent_conversations",
        "slots": {"limit": 3, "platform": "chatwoot"},
        "execution_mode": "api",
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert result["platform"] == "chatwoot"
    assert result["provider_id"] == "chatwoot"
    assert "最近会话数：3" in result["result_summary"]


def test_woo_query_mock_path_not_regressed():
    state = {
        "intent_code": "product.query_sku_status",
        "slots": {"sku": "A001", "platform": "mock"},
        "execution_mode": "mock",
        "status": "processing",
    }
    result = execute_action(state)
    assert result["status"] == "succeeded"
    assert "SKU: A001" in result["result_summary"]
