"""Controlled HTML page for Playwright RPA (dev only; not for Feishu users)."""
from __future__ import annotations

import html

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.core.config import settings

router = APIRouter(prefix="/internal/rpa-sandbox", tags=["internal-rpa-sandbox"])


@router.get("/update-price", include_in_schema=False, response_class=HTMLResponse)
def rpa_update_price_sandbox_page(
    sku: str = Query(default="A001", description="SKU to display"),
    current_price: float = Query(default=59.9, description="Current price shown on page"),
    target_price: float = Query(default=39.9, description="Prefill target input"),
    force_fail: int = Query(default=0, ge=0, le=1, description="1 = submit always fails (dev)"),
):
    """
    Minimal page: SKU, current price, target input, submit, result region.
    Playwright runner drives this URL — not a production admin UI.
    """
    if not settings.ENABLE_INTERNAL_SANDBOX_API:
        raise HTTPException(status_code=503, detail="internal sandbox api disabled")

    sku_e = html.escape(sku.strip().upper()[:64])
    cf = float(current_price)
    tf = float(target_price)
    ff = 1 if force_fail else 0

    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>RPA update-price sandbox</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 480px; margin: 2rem auto; padding: 0 1rem; }}
    h1 {{ font-size: 1.1rem; }}
    label {{ display: block; margin: 0.5rem 0 0.2rem; }}
    input[type="number"] {{ width: 100%; padding: 0.4rem; box-sizing: border-box; }}
    button {{ margin-top: 1rem; padding: 0.5rem 1rem; cursor: pointer; }}
    #result {{ margin-top: 1rem; padding: 0.75rem; border: 1px solid #ccc; min-height: 2rem; }}
    #result[data-status="error"] {{ border-color: #c00; background: #fff5f5; }}
    #result[data-status="success"] {{ border-color: #080; background: #f5fff5; }}
  </style>
</head>
<body
  data-testid="sandbox-root"
  data-sku="{sku_e}"
  data-current-price="{cf:.4f}"
  data-force-fail="{ff}"
>
  <h1>RPA sandbox — update price</h1>
  <p>SKU: <strong id="sku-display" data-testid="sku">{sku_e}</strong></p>
  <p>当前价格: <span id="current-price" data-testid="current-price">{cf:.2f}</span></p>
  <label for="target-price">目标价格</label>
  <input id="target-price" data-testid="target-price" type="number" step="0.01" value="{tf:.2f}"/>
  <button type="button" id="submit-btn" data-testid="submit">提交改价</button>
  <div id="result" data-testid="result" data-status="">等待提交…</div>
  <script>
    (function () {{
      var btn = document.getElementById("submit-btn");
      var tgt = document.getElementById("target-price");
      var out = document.getElementById("result");
      var body = document.body;
      btn.addEventListener("click", function () {{
        var ff = body.getAttribute("data-force-fail") === "1";
        var cur = parseFloat(body.getAttribute("data-current-price") || "0");
        var v = parseFloat(tgt.value);
        if (isNaN(v)) {{
          out.setAttribute("data-status", "error");
          out.removeAttribute("data-new-price");
          out.removeAttribute("data-old-price");
          out.textContent = "无效价格";
          return;
        }}
        if (ff) {{
          out.setAttribute("data-status", "error");
          out.removeAttribute("data-new-price");
          out.removeAttribute("data-old-price");
          out.textContent = "Sandbox forced failure (dev)";
          return;
        }}
        out.setAttribute("data-status", "success");
        out.setAttribute("data-old-price", String(cur));
        out.setAttribute("data-new-price", String(v));
        out.textContent = "成功：价格已更新为 " + v;
      }});
    }})();
  </script>
</body>
</html>"""
    return HTMLResponse(content=page)
