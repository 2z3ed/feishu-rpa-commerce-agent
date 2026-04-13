from app.graph.nodes.resolve_intent import resolve_intent


def test_resolve_odoo_inventory_intent():
    state = {"normalized_text": "查 Odoo 里 SKU A001 的库存"}
    out = resolve_intent(state)
    assert out["intent_code"] == "warehouse.query_inventory"
    assert out["slots"]["sku"] == "A001"
    assert out["slots"]["platform"] == "odoo"


def test_resolve_chatwoot_recent_conversations_intent():
    state = {"normalized_text": "查 Chatwoot 最近 5 个会话"}
    out = resolve_intent(state)
    assert out["intent_code"] == "customer.list_recent_conversations"
    assert out["slots"]["platform"] == "chatwoot"
    assert out["slots"]["limit"] == 5
