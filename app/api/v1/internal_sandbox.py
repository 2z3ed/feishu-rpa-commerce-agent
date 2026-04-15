"""Internal sandbox endpoints for development/testing only."""
from fastapi import APIRouter, HTTPException, Query
from app.core.config import settings

router = APIRouter(prefix="/internal/sandbox", tags=["internal-sandbox"])

_BASE_SKU_DATA = {
    "A001": {"sku": "A001", "status": "active", "inventory": 120, "price": 59.9},
    "A002": {"sku": "A002", "status": "inactive", "inventory": 0, "price": 99.0},
}

_PLATFORM_PROFILE = {
    "sandbox": {"name_prefix": "API沙箱商品", "inventory_offset": 0},
    "woo": {"name_prefix": "Woo商品", "inventory_offset": 10},
    "odoo": {"name_prefix": "Odoo商品", "inventory_offset": -5},
    "mock": {"name_prefix": "Mock网关商品", "inventory_offset": 0},
}

# Mutable in-memory override for controlled Odoo inventory write samples (P6.1).
# Keyed by SKU upper. Values are absolute inventory ints.
_ODOO_INVENTORY_OVERRIDE: dict[str, int] = {}

_CHATWOOT_CONVERSATIONS = [
    {"conversation_id": 123, "status": "open", "last_message": "您好，请问订单什么时候发货？", "customer_name": "Alice"},
    {"conversation_id": 122, "status": "pending", "last_message": "可以帮我改收货地址吗？", "customer_name": "Bob"},
    {"conversation_id": 121, "status": "resolved", "last_message": "收到，谢谢！", "customer_name": "Carol"},
    {"conversation_id": 120, "status": "open", "last_message": "申请退款，商品有破损。", "customer_name": "David"},
    {"conversation_id": 119, "status": "pending", "last_message": "物流单号查不到。", "customer_name": "Eve"},
]


def _build_provider_payload(sku_upper: str, platform_key: str):
    if not settings.ENABLE_INTERNAL_SANDBOX_API:
        raise HTTPException(status_code=503, detail="internal sandbox api disabled")

    # Minimal deterministic error simulation for client testing.
    if sku_upper == "ERR_TIMEOUT":
        raise HTTPException(status_code=504, detail="sandbox timeout")
    if sku_upper == "ERR_CLIENT":
        raise HTTPException(status_code=502, detail="sandbox client error")
    if sku_upper == "ERR_MAPPER":
        # Deliberately malformed payload for mapper error test.
        return {"provider": platform_key, "payload": {"broken": True}}

    record = _BASE_SKU_DATA.get(sku_upper)
    if not record:
        raise HTTPException(status_code=404, detail=f"SKU {sku_upper} not found")

    profile = _PLATFORM_PROFILE.get(platform_key) or _PLATFORM_PROFILE["sandbox"]
    base_name = f"{profile['name_prefix']} {record['sku']}"
    base_inventory = max(0, record["inventory"] + profile["inventory_offset"])
    if platform_key == "odoo":
        if sku_upper in _ODOO_INVENTORY_OVERRIDE:
            base_inventory = max(0, int(_ODOO_INVENTORY_OVERRIDE[sku_upper]))

    if platform_key == "woo":
        return {
            "provider": "woo",
            "payload": {
                "id": 10001 if record["sku"] == "A001" else 10002,
                "name": base_name,
                "sku": record["sku"],
                "status": record["status"],
                "manage_stock": True,
                "stock_quantity": base_inventory,
                "regular_price": f"{record['price']:.2f}",
                "price": f"{record['price']:.2f}",
                "type": "simple",
            },
        }
    if platform_key == "odoo":
        return {
            "provider": "odoo",
            "payload": {
                "default_code": record["sku"],
                "display_name": base_name,
                "active": record["status"] == "active",
                "qty_available": base_inventory,
                "list_price": record["price"],
            },
        }
    return {
        "provider": "sandbox",
        "payload": {
            "sku": record["sku"],
            "name": base_name,
            "state": record["status"],
            "qty": base_inventory,
            "sale_price": record["price"],
        },
    }


@router.get("/product/sku/{sku}", include_in_schema=False)
def query_sku_status_sandbox(
    sku: str,
    platform: str = Query(default="sandbox"),
):
    sku_upper = sku.upper()
    platform_key = platform.lower().strip()
    if platform_key not in _PLATFORM_PROFILE:
        platform_key = "sandbox"
    return _build_provider_payload(sku_upper, platform_key)


@router.get("/provider/sandbox/sku/{sku}", include_in_schema=False)
def provider_sandbox_query_sku(sku: str, provider_platform: str = Query(default="sandbox")):
    return _build_provider_payload(sku.upper(), "sandbox")


@router.get("/provider/woo/wp-json/wc/v3/products", include_in_schema=False)
def provider_woo_query_products(
    sku: str = Query(...),
    status: str = Query(default="any"),
    per_page: int = Query(default=1),
    consumer_key: str = Query(default="ck_placeholder"),
):
    _ = (status, per_page, consumer_key)
    return _build_provider_payload(sku.upper(), "woo")


@router.get("/provider/odoo/product/{sku}", include_in_schema=False)
def provider_odoo_query_sku(sku: str, company: str = Query(default="main")):
    return _build_provider_payload(sku.upper(), "odoo")


@router.post("/provider/odoo/inventory/adjust", include_in_schema=False)
def provider_odoo_adjust_inventory(
    sku: str = Query(...),
    delta: int = Query(...),
):
    """Controlled, non-production inventory adjustment for P6.1 acceptance only.

    This endpoint mutates in-memory override used by provider_odoo_query_sku.
    """
    if not settings.ENABLE_INTERNAL_SANDBOX_API:
        raise HTTPException(status_code=503, detail="internal sandbox api disabled")
    sku_upper = (sku or "").upper()
    if not sku_upper:
        raise HTTPException(status_code=400, detail="sku is required")
    if sku_upper not in _BASE_SKU_DATA:
        raise HTTPException(status_code=404, detail=f"SKU {sku_upper} not found")
    try:
        d = int(delta)
    except Exception:
        raise HTTPException(status_code=400, detail="delta must be int")
    if d == 0:
        raise HTTPException(status_code=400, detail="delta must be non-zero")

    # Derive current inventory from base + offset + existing override.
    current_payload = _build_provider_payload(sku_upper, "odoo")
    current_qty = int(((current_payload or {}).get("payload") or {}).get("qty_available") or 0)
    new_qty = max(0, int(current_qty + d))
    _ODOO_INVENTORY_OVERRIDE[sku_upper] = new_qty
    return {
        "provider": "odoo",
        "payload": {
            "default_code": sku_upper,
            "qty_before": current_qty,
            "delta": d,
            "qty_after": new_qty,
            "updated": True,
        },
    }

@router.get("/provider/chatwoot/conversations/recent", include_in_schema=False)
def provider_chatwoot_recent_conversations(limit: int = Query(default=5, ge=1, le=20)):
    if not settings.ENABLE_INTERNAL_SANDBOX_API:
        raise HTTPException(status_code=503, detail="internal sandbox api disabled")
    return {"provider": "chatwoot", "payload": {"conversations": _CHATWOOT_CONVERSATIONS[:limit], "limit": limit}}
