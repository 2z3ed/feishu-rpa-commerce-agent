"""Admin-style controlled pages for browser_real RPA (dev only; not production)."""
from __future__ import annotations

import html
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.core.config import settings

router = APIRouter(prefix="/internal/rpa-sandbox/admin-like", tags=["internal-rpa-admin-like"])

_VALID_FAILURE = frozenset({"none", "sku_missing", "save_error", "save_disabled"})


def _norm_failure_mode(raw: str) -> str:
    v = (raw or "none").lower().strip()
    return v if v in _VALID_FAILURE else "none"


@router.get("", include_in_schema=False, response_class=HTMLResponse)
def admin_like_hub(
    sku: str = Query(default="A001"),
    current_price: float = Query(default=59.9),
    target_price: float = Query(default=39.9),
    failure_mode: str = Query(default="none"),
):
    """Fake admin home: one navigation step before the update-price workbench."""
    if not settings.ENABLE_INTERNAL_SANDBOX_API:
        raise HTTPException(status_code=503, detail="internal sandbox api disabled")

    fm = _norm_failure_mode(failure_mode)
    sku_e = html.escape(sku.strip().upper()[:64])
    q = urlencode(
        {
            "sku": sku.strip().upper()[:64],
            "current_price": f"{float(current_price):.4f}",
            "target_price": f"{float(target_price):.4f}",
            "failure_mode": fm,
        }
    )
    next_path = f"/api/v1/internal/rpa-sandbox/admin-like/update-price?{q}"

    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Commerce 后台 · 概览</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: system-ui, sans-serif; background: #f0f2f5; color: #1f1f1f; }}
    .topbar {{
      height: 48px; background: #001529; color: #fff; display: flex; align-items: center;
      padding: 0 16px; font-size: 15px; font-weight: 600;
    }}
    .layout {{ display: flex; min-height: calc(100vh - 48px); }}
    .sider {{
      width: 200px; background: #fff; border-right: 1px solid #e8e8e8; padding: 12px 0;
    }}
    .sider a {{
      display: block; padding: 10px 16px; color: #333; text-decoration: none; font-size: 14px;
    }}
    .sider a:hover {{ background: #f5f5f5; }}
    .content {{ flex: 1; padding: 24px; }}
    .card {{
      background: #fff; border-radius: 8px; padding: 20px; max-width: 560px;
      box-shadow: 0 1px 2px rgba(0,0,0,.06);
    }}
    h1 {{ margin: 0 0 8px; font-size: 18px; }}
    .muted {{ color: #888; font-size: 13px; margin-bottom: 16px; }}
  </style>
</head>
<body data-testid="admin-hub-root">
  <header class="topbar" data-testid="admin-topbar">Commerce 后台（RPA 受控环境）</header>
  <div class="layout">
    <aside class="sider" data-testid="admin-sider">
      <span style="padding:0 16px;font-size:12px;color:#999;">目录</span>
      <a href="{html.escape(next_path)}" data-testid="nav-to-update-price">商品 · 改价</a>
    </aside>
    <main class="content">
      <div class="card">
        <h1>工作台</h1>
        <p class="muted">当前会话 SKU 预览：<strong data-testid="hub-sku-hint">{sku_e}</strong></p>
        <p class="muted">请从左侧进入「商品 · 改价」完成受控 RPA 流程。</p>
      </div>
    </main>
  </div>
</body>
</html>"""
    return HTMLResponse(content=page)


@router.get("/update-price", include_in_schema=False, response_class=HTMLResponse)
def admin_like_update_price_page(
    sku: str = Query(default="A001"),
    current_price: float = Query(default=59.9),
    target_price: float = Query(default=39.9),
    failure_mode: str = Query(default="none"),
):
    """
    Admin-like workbench: search SKU, product card, new price, save, result strip.
    failure_mode: none | sku_missing | save_error | save_disabled
    """
    if not settings.ENABLE_INTERNAL_SANDBOX_API:
        raise HTTPException(status_code=503, detail="internal sandbox api disabled")

    fm = _norm_failure_mode(failure_mode)
    sku_u = sku.strip().upper()[:64]
    sku_e = html.escape(sku_u)
    cf = float(current_price)
    tf = float(target_price)
    save_disabled_attr = "disabled" if fm == "save_disabled" else ""

    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Commerce 后台 · 商品改价</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: system-ui, sans-serif; background: #f0f2f5; color: #1f1f1f; }}
    .topbar {{
      height: 48px; background: #001529; color: #fff; display: flex; align-items: center;
      padding: 0 16px; font-size: 15px; font-weight: 600;
    }}
    .breadcrumb {{ font-size: 12px; color: #8c8c8c; padding: 12px 24px; }}
    .main {{ padding: 0 24px 32px; max-width: 720px; }}
    .panel {{
      background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 16px;
      box-shadow: 0 1px 2px rgba(0,0,0,.06);
    }}
    h1 {{ margin: 0 0 4px; font-size: 18px; }}
    .sub {{ color: #8c8c8c; font-size: 13px; margin-bottom: 16px; }}
    label {{ display: block; font-size: 13px; margin: 8px 0 4px; color: #595959; }}
    input[type="text"], input[type="number"] {{
      width: 100%; max-width: 320px; padding: 8px 10px; border: 1px solid #d9d9d9; border-radius: 4px;
    }}
    button.primary {{
      margin-top: 12px; padding: 8px 20px; background: #1677ff; color: #fff; border: none;
      border-radius: 4px; cursor: pointer; font-size: 14px;
    }}
    button.primary:disabled {{ background: #bfbfbf; cursor: not-allowed; }}
    .card {{
      margin-top: 16px; padding: 16px; border: 1px solid #e8e8e8; border-radius: 8px; background: #fafafa;
      display: none;
    }}
    .card[data-visible="1"] {{ display: block; }}
    .err-strip {{
      display: none; margin-top: 12px; padding: 10px 12px; border-radius: 4px;
      background: #fff2f0; border: 1px solid #ffccc7; color: #a8071a; font-size: 14px;
    }}
    .err-strip[data-status="error"] {{ display: block; }}
    #result {{
      margin-top: 16px; padding: 12px; border: 1px solid #d9d9d9; border-radius: 4px; min-height: 44px;
      font-size: 14px;
    }}
    #result[data-status="error"] {{ border-color: #ff7875; background: #fff2f0; }}
    #result[data-status="success"] {{ border-color: #52c41a; background: #f6ffed; }}
  </style>
</head>
<body
  data-testid="admin-update-root"
  data-failure-mode="{html.escape(fm)}"
  data-sku="{sku_e}"
  data-current-price="{cf:.4f}"
>
  <header class="topbar" data-testid="admin-topbar">Commerce 后台 · 商品中心</header>
  <div class="breadcrumb" data-testid="breadcrumb">首页 / 商品 / 改价</div>
  <div class="main">
    <div class="panel">
      <h1>商品改价</h1>
      <p class="sub">搜索并编辑价格（受控页面，非生产环境）</p>
      <label for="sku-search">SKU 搜索</label>
      <input type="text" id="sku-search" data-testid="sku-search" value="{sku_e}" autocomplete="off"/>
      <button type="button" class="primary" id="locate-btn" data-testid="locate-sku">定位商品</button>
      <div id="global-error" class="err-strip" data-testid="global-error" data-status=""></div>
      <div id="product-card" class="card" data-testid="product-card" data-visible="0">
        <div><strong>SKU</strong> <span id="card-sku" data-testid="card-sku"></span></div>
        <div style="margin-top:8px;"><strong>当前价格</strong>
          <span id="card-current" data-testid="card-current-price"></span></div>
        <label for="new-price" style="margin-top:12px;">新价格</label>
        <input type="number" step="0.01" id="new-price" data-testid="new-price" value="{tf:.2f}"/>
        <div>
          <button type="button" class="primary" id="save-price" data-testid="save-price" {save_disabled_attr}>保存</button>
        </div>
      </div>
      <div id="result" data-testid="result" data-status="">操作结果将显示在此处</div>
    </div>
  </div>
  <script>
    (function () {{
      var mode = document.body.getAttribute("data-failure-mode") || "none";
      var dataSku = document.body.getAttribute("data-sku") || "";
      var dataCur = parseFloat(document.body.getAttribute("data-current-price") || "0");
      var search = document.getElementById("sku-search");
      var locate = document.getElementById("locate-btn");
      var gerr = document.getElementById("global-error");
      var card = document.getElementById("product-card");
      var cardSku = document.getElementById("card-sku");
      var cardCur = document.getElementById("card-current");
      var newp = document.getElementById("new-price");
      var save = document.getElementById("save-price");
      var out = document.getElementById("result");

      locate.addEventListener("click", function () {{
        gerr.setAttribute("data-status", "");
        gerr.textContent = "";
        card.setAttribute("data-visible", "0");
        out.setAttribute("data-status", "");
        out.textContent = "操作结果将显示在此处";

        var q = (search.value || "").trim().toUpperCase();
        if (mode === "sku_missing") {{
          gerr.setAttribute("data-status", "error");
          gerr.textContent = "未找到该 SKU 对应的商品（受控失败：sku_missing）";
          return;
        }}
        if (q !== dataSku) {{
          gerr.setAttribute("data-status", "error");
          gerr.textContent = "SKU 与当前任务不一致，无法定位商品卡片";
          return;
        }}
        cardSku.textContent = dataSku;
        cardCur.textContent = dataCur.toFixed(2);
        card.setAttribute("data-visible", "1");
      }});

      save.addEventListener("click", function () {{
        if (save.disabled) {{
          out.setAttribute("data-status", "error");
          out.textContent = "保存按钮不可用（受控失败：save_disabled）";
          return;
        }}
        var v = parseFloat(newp.value);
        if (isNaN(v)) {{
          out.setAttribute("data-status", "error");
          out.removeAttribute("data-new-price");
          out.removeAttribute("data-old-price");
          out.textContent = "价格格式无效";
          return;
        }}
        if (mode === "save_error") {{
          out.setAttribute("data-status", "error");
          out.removeAttribute("data-new-price");
          out.removeAttribute("data-old-price");
          out.textContent = "保存失败：服务端校验错误（受控失败：save_error）";
          return;
        }}
        out.setAttribute("data-status", "success");
        out.setAttribute("data-old-price", String(dataCur));
        out.setAttribute("data-new-price", String(v));
        out.textContent = "已保存：价格更新为 " + v;
      }});
    }})();
  </script>
</body>
</html>"""
    return HTMLResponse(content=page)
