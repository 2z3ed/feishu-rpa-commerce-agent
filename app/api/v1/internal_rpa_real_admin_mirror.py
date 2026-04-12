"""Minimal HTML mirror for P4.2 real_admin_prepared local验收（配置驱动 URL 指向本服务即可）。"""
from __future__ import annotations

import html

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from app.core.config import settings

router = APIRouter(prefix="/internal/rpa-real-admin-mirror", tags=["internal-rpa-real-admin-mirror"])


def _guard() -> None:
    if not settings.ENABLE_INTERNAL_SANDBOX_API:
        raise HTTPException(status_code=503, detail="internal sandbox api disabled")


@router.get("/home", include_in_schema=False, response_class=HTMLResponse)
def real_admin_mirror_home():
    _guard()
    return HTMLResponse(
        """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/><title>mirror home</title></head>
<body data-testid="real-admin-home-root">
  <h1>Mirror — home</h1>
  <p>P4.2 real_admin_prepared 本地 mirror：home</p>
</body></html>"""
    )


@router.get("/catalog", include_in_schema=False, response_class=HTMLResponse)
def real_admin_mirror_catalog(request: Request):
    """接受任意 query 键（与 RPA_REAL_ADMIN_SKU_SEARCH_PARAM 一致）；值 __MIRROR_EMPTY__ 或 mirror_empty=1 表示无结果。"""
    _guard()
    params = dict(request.query_params)
    mirror_raw = (params.pop("mirror_empty", "0") or "0").strip()
    try:
        mirror_empty = int(mirror_raw)
    except ValueError:
        mirror_empty = 0
    mirror_empty = 1 if mirror_empty else 0
    sku_vals = [str(v).strip() for v in params.values()]
    empty = mirror_empty == 1 or any(v == "__MIRROR_EMPTY__" for v in sku_vals)
    empty_vis = "1" if empty else "0"
    res_vis = "0" if empty else "1"
    q_e = html.escape(",".join(f"{k}={v}" for k, v in params.items())[:256] or "(no sku query)")
    body = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/><title>mirror catalog</title></head>
<body data-testid="real-admin-catalog-body">
  <h1>Mirror — catalog</h1>
  <p>query q=<strong>{q_e}</strong></p>
  <div id="real-admin-catalog-empty" data-testid="real-admin-catalog-empty" data-visible="{empty_vis}">
    {"无匹配 SKU（mirror）" if empty else ""}
  </div>
  <div id="real-admin-catalog-results" data-testid="real-admin-catalog-results" data-visible="{res_vis}">
    {"（有结果，继续 detail）" if not empty else ""}
  </div>
</body></html>"""
    return HTMLResponse(body)


@router.get("/detail/{sku}", include_in_schema=False, response_class=HTMLResponse)
def real_admin_mirror_detail(
    sku: str,
    mirror_fail: str = Query(
        default="none",
        description="none | missing_price — 模拟 detail 关键选择器缺失",
    ),
):
    _guard()
    sku_u = sku.strip().upper()[:64]
    sku_e = html.escape(sku_u)
    fail = (mirror_fail or "none").lower().strip()
    price_block = ""
    if fail != "missing_price":
        price_block = (
            f'<p>当前价: <span id="mirror-price" data-testid="real-admin-current-price">59.90</span></p>'
        )
    new_price_block = (
        f'<label>目标价<input id="mirror-new-price" data-testid="real-admin-new-price" type="number" '
        f'step="0.01" value="59.90"/></label>'
    )
    body = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/><title>mirror detail</title></head>
<body data-testid="real-admin-detail-root">
  <h1>Mirror — detail</h1>
  <p>SKU: <span data-testid="real-admin-page-sku">{sku_e}</span></p>
  {price_block}
  {new_price_block}
  <p>状态: <span data-testid="real-admin-status">ok</span></p>
  <p>说明: <span data-testid="real-admin-message">mirror detail loaded</span></p>
</body></html>"""
    return HTMLResponse(body)
