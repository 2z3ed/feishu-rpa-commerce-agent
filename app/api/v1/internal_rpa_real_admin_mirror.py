"""Minimal HTML mirror for P4.2 real_admin_prepared local验收（配置驱动 URL 指向本服务即可）。"""
from __future__ import annotations

import html
import json

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
        description=(
            "none | missing_price | input_missing | save_missing | save_disabled | submit_failed | "
            "submit_no_effect | save_result_timeout | save_result_error | post_save_price_mismatch | post_save_readback_missing"
        ),
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
    new_price_block = ""
    if fail != "input_missing":
        new_price_block = (
            f'<label>目标价<input id="mirror-new-price" data-testid="real-admin-new-price" type="number" '
            f'step="0.01" value="59.90"/></label>'
        )

    save_btn_block = ""
    if fail != "save_missing":
        disabled_attr = " disabled" if fail == "save_disabled" else ""
        save_btn_block = (
            f'<button id="mirror-save-btn" data-testid="real-admin-save-btn"{disabled_attr}>保存</button>'
        )

    # save result is always present in DOM for selector stability (may stay hidden on timeout mode)
    save_result_block = (
        '<div id="mirror-save-result" data-testid="real-admin-save-result" '
        'data-status="idle" data-visible="0" style="margin-top:12px;color:#333;"></div>'
    )

    # Controlled behavior via inline JS: click -> set result + optionally mutate readback.
    # NOTE: script tags don't decode HTML entities; use JSON string literal to avoid JS parse errors.
    js = f"""
<script>
(() => {{
  const FAIL = {json.dumps(fail)};
  const priceEl = document.querySelector('#mirror-price');
  const inputEl = document.querySelector('#mirror-new-price');
  const saveBtn = document.querySelector('#mirror-save-btn');
  const resultEl = document.querySelector('#mirror-save-result');
  function setResult(status, text) {{
    if (!resultEl) return;
    resultEl.setAttribute('data-status', status);
    resultEl.setAttribute('data-visible', '1');
    resultEl.textContent = text || '';
  }}
  if (saveBtn) {{
    saveBtn.addEventListener('click', (e) => {{
      e.preventDefault();
      if (FAIL === 'submit_failed') {{
        setResult('error', '提交失败（mirror submit_failed）');
        return;
      }}
      if (FAIL === 'submit_no_effect') {{
        // Visible but no effective status change (gray area)
        setResult('idle', '');
        return;
      }}
      if (FAIL === 'save_result_timeout') {{
        // Keep result hidden forever.
        return;
      }}
      if (FAIL === 'save_result_error') {{
        setResult('error', '保存失败（mirror save_result_error）');
        return;
      }}
      const v = inputEl ? String(inputEl.value || '').trim() : '';
      setResult('success', '保存成功（mirror）');
      // post-save readback mutation
      if (FAIL === 'post_save_readback_missing') {{
        if (priceEl && priceEl.parentElement) priceEl.parentElement.removeChild(priceEl);
        return;
      }}
      if (priceEl) {{
        if (FAIL === 'post_save_price_mismatch') {{
          priceEl.textContent = '66.60';
        }} else {{
          priceEl.textContent = v || '59.90';
        }}
      }}
    }});
  }}
}})();
</script>
"""
    body = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/><title>mirror detail</title></head>
<body data-testid="real-admin-detail-root">
  <h1>Mirror — detail</h1>
  <p>SKU: <span data-testid="real-admin-page-sku">{sku_e}</span></p>
  {price_block}
  {new_price_block}
  {save_btn_block}
  {save_result_block}
  <p>状态: <span data-testid="real-admin-status">ok</span></p>
  <p>说明: <span data-testid="real-admin-message">mirror detail loaded</span></p>
  {js}
</body></html>"""
    return HTMLResponse(body)
