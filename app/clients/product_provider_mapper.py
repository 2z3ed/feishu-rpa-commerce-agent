"""Provider response mappers for product.query_sku_status."""
from __future__ import annotations

from typing import Callable
from dataclasses import dataclass


class ProductApiMapperError(Exception):
    """Raised when provider raw payload cannot be mapped."""


@dataclass
class MappedProductSkuStatus:
    sku: str
    product_name: str
    status: str
    inventory: int
    price: float
    platform: str


def map_sandbox_payload(raw_payload: dict, platform: str) -> MappedProductSkuStatus:
    required = {"sku", "name", "state", "qty", "sale_price"}
    if not required.issubset(raw_payload.keys()):
        raise ProductApiMapperError("sandbox payload missing required fields")
    return MappedProductSkuStatus(
        sku=str(raw_payload["sku"]),
        product_name=str(raw_payload["name"]),
        status=str(raw_payload["state"]),
        inventory=int(raw_payload["qty"]),
        price=float(raw_payload["sale_price"]),
        platform=platform,
    )


def map_woo_payload(raw_payload: dict, platform: str) -> MappedProductSkuStatus:
    required = {"sku", "name", "status", "stock_quantity", "price"}
    if not required.issubset(raw_payload.keys()):
        raise ProductApiMapperError("woo payload missing required fields")
    return MappedProductSkuStatus(
        sku=str(raw_payload["sku"]),
        product_name=str(raw_payload["name"]),
        status=str(raw_payload["status"]),
        inventory=int(raw_payload["stock_quantity"]),
        price=float(raw_payload["price"]),
        platform=platform,
    )


def map_odoo_payload(raw_payload: dict, platform: str) -> MappedProductSkuStatus:
    required = {"default_code", "display_name", "active", "qty_available", "list_price"}
    if not required.issubset(raw_payload.keys()):
        raise ProductApiMapperError("odoo payload missing required fields")
    return MappedProductSkuStatus(
        sku=str(raw_payload["default_code"]),
        product_name=str(raw_payload["display_name"]),
        status="active" if bool(raw_payload["active"]) else "inactive",
        inventory=int(raw_payload["qty_available"]),
        price=float(raw_payload["list_price"]),
        platform=platform,
    )


def get_mapper(platform: str) -> tuple[str, Callable[[dict, str], MappedProductSkuStatus]]:
    platform_key = (platform or "sandbox").lower().strip()
    if platform_key == "woo":
        return "woo_mapper", map_woo_payload
    if platform_key == "odoo":
        return "odoo_mapper", map_odoo_payload
    return "sandbox_mapper", map_sandbox_payload
