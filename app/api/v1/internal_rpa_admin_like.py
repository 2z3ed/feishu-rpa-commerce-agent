"""Admin-style controlled pages for browser_real RPA (dev only; not production)."""
from __future__ import annotations

import html
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.core.config import settings

router = APIRouter(prefix="/internal/rpa-sandbox/admin-like", tags=["internal-rpa-admin-like"])

_VALID_FAILURE = frozenset({"none", "sku_missing", "save_error", "save_disabled"})
_VALID_LIST_DETAIL_FAILURE = frozenset(
    {"none", "sku_missing_in_list", "detail_page_not_found", "save_button_disabled", "save_error"}
)
_VALID_INVENTORY_FAILURE = frozenset({"none", "element_missing", "page_timeout"})


def _norm_failure_mode(raw: str) -> str:
    v = (raw or "none").lower().strip()
    return v if v in _VALID_FAILURE else "none"


def _norm_list_detail_failure_mode(raw: str) -> str:
    v = (raw or "none").lower().strip()
    return v if v in _VALID_LIST_DETAIL_FAILURE else "none"

def _norm_inventory_failure_mode(raw: str) -> str:
    v = (raw or "none").lower().strip()
    return v if v in _VALID_INVENTORY_FAILURE else "none"


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

    sku_u = sku.strip().upper()[:64]
    sku_e = html.escape(sku_u)
    cf_s = f"{float(current_price):.4f}"
    tf_s = f"{float(target_price):.4f}"
    base_q = {"sku": sku_u, "current_price": cf_s, "target_price": tf_s}
    # Hub is shared by admin_like (workbench) and list_detail (catalog → detail). List-detail modes
    # (e.g. detail_page_not_found) are not valid for /update-price; keep them on the catalog link only.
    q_update = urlencode({**base_q, "failure_mode": _norm_failure_mode(failure_mode)})
    q_catalog = urlencode({**base_q, "failure_mode": _norm_list_detail_failure_mode(failure_mode)})
    next_path = f"/api/v1/internal/rpa-sandbox/admin-like/update-price?{q_update}"
    catalog_path = f"/api/v1/internal/rpa-sandbox/admin-like/catalog?{q_catalog}"
    # Inventory adjust uses its own failure modes (element_missing/page_timeout); keep it separate.
    inv_q = urlencode(
        {
            "sku": sku_u,
            "old_inventory": 100,
            "delta": 5,
            "target_inventory": 105,
            "failure_mode": _norm_inventory_failure_mode(failure_mode),
        }
    )
    inv_dash = "/api/v1/internal/rpa-sandbox/admin-like/inventory"
    inv_adjust = f"/api/v1/internal/rpa-sandbox/admin-like/inventory/adjust?{inv_q}"

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
      <a href="{html.escape(catalog_path)}" data-testid="nav-to-catalog">商品 · 目录</a>
      <a href="{html.escape(next_path)}" data-testid="nav-to-update-price">商品 · 改价（工作台）</a>
      <a href="{html.escape(inv_dash)}" data-testid="nav-to-inventory-dash">库存 · 概览</a>
      <a href="{html.escape(inv_adjust)}" data-testid="nav-to-inventory-adjust">库存 · 调整（工作台）</a>
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


@router.get("/inventory", include_in_schema=False, response_class=HTMLResponse)
def inventory_dashboard_page(
    tenant: str = Query(default="sandbox"),
    role: str = Query(default="warehouse_operator"),
):
    """Inventory dashboard entry (dev only; not production)."""
    if not settings.ENABLE_INTERNAL_SANDBOX_API:
        raise HTTPException(status_code=503, detail="internal sandbox api disabled")
    ten = html.escape((tenant or "sandbox").strip()[:32])
    rl = html.escape((role or "warehouse_operator").strip()[:32])
    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Commerce 后台 · 库存概览</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: system-ui, sans-serif; background: #f0f2f5; color: #1f1f1f; }}
    .topbar {{ height: 48px; background: #001529; color: #fff; display:flex; align-items:center; padding:0 16px; font-weight:600; }}
    .layout {{ display:flex; min-height: calc(100vh - 48px); }}
    .sider {{ width: 220px; background:#fff; border-right:1px solid #e8e8e8; padding: 12px 0; }}
    .sider a {{ display:block; padding:10px 16px; color:#333; text-decoration:none; font-size:14px; }}
    .sider a:hover {{ background:#f5f5f5; }}
    .content {{ flex:1; padding:24px; }}
    .card {{ background:#fff; border-radius:8px; padding:20px; max-width:720px; box-shadow:0 1px 2px rgba(0,0,0,.06); }}
    .meta {{ color:#888; font-size:13px; margin: 8px 0 0; }}
    .badge {{ display:inline-block; padding:2px 8px; border-radius:999px; background:#fff1b8; color:#614700; font-size:12px; margin-left:8px; }}
  </style>
</head>
<body data-testid="inventory-dashboard-root" data-tenant="{ten}" data-role="{rl}">
  <header class="topbar" data-testid="inventory-topbar">
    Commerce 后台 · 库存中心 <span class="badge" data-testid="nonprod-badge">SANDBOX / 非生产</span>
  </header>
  <div class="layout">
    <aside class="sider" data-testid="inventory-sider">
      <span style="padding:0 16px;font-size:12px;color:#999;">库存中心</span>
      <a href="/api/v1/internal/rpa-sandbox/admin-like/inventory" data-testid="nav-inv-home">概览</a>
      <a href="/api/v1/internal/rpa-sandbox/admin-like/inventory/adjust" data-testid="nav-inv-adjust">库存调整</a>
    </aside>
    <main class="content">
      <div class="card">
        <h1 style="margin:0 0 8px;font-size:18px;">库存概览</h1>
        <p class="meta">租户：<strong data-testid="tenant">{ten}</strong>，角色：<strong data-testid="role">{rl}</strong></p>
        <p class="meta">此页面仅用于 RPA 受控验证，不代表真实生产后台。</p>
      </div>
    </main>
  </div>
</body>
</html>"""
    return HTMLResponse(content=page)


@router.get("/inventory/adjust", include_in_schema=False, response_class=HTMLResponse)
def inventory_adjust_page(
    sku: str = Query(default="A001"),
    old_inventory: int = Query(default=100),
    delta: int = Query(default=5),
    target_inventory: int = Query(default=105),
    failure_mode: str = Query(default="none"),
):
    """Inventory adjust workbench: list search -> drawer edit -> submit -> result."""
    if not settings.ENABLE_INTERNAL_SANDBOX_API:
        raise HTTPException(status_code=503, detail="internal sandbox api disabled")
    fm = _norm_inventory_failure_mode(failure_mode)
    sku_u = sku.strip().upper()[:64]
    sku_e = html.escape(sku_u)
    oi = int(old_inventory)
    d = int(delta)
    ti = int(target_inventory)
    # Controlled knobs:
    # - element_missing: drawer will never render
    # - page_timeout: result never becomes visible
    drawer_visible = "0" if fm == "element_missing" else "0"
    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>库存调整 · 工作台</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: system-ui, sans-serif; background: #f0f2f5; color: #1f1f1f; }}
    .topbar {{ height: 48px; background: #001529; color: #fff; display:flex; align-items:center; padding:0 16px; font-weight:600; }}
    .layout {{ display:flex; min-height: calc(100vh - 48px); }}
    .sider {{ width: 220px; background:#fff; border-right:1px solid #e8e8e8; padding: 12px 0; }}
    .sider a {{ display:block; padding:10px 16px; color:#333; text-decoration:none; font-size:14px; }}
    .sider a:hover {{ background:#f5f5f5; }}
    .content {{ flex:1; padding:20px 24px; max-width: 1100px; }}
    .breadcrumb {{ font-size: 12px; color: #8c8c8c; margin-bottom: 12px; }}
    .panel {{ background:#fff; border-radius:8px; padding:16px 20px; box-shadow:0 1px 2px rgba(0,0,0,.06); }}
    .row {{ display:flex; gap: 16px; flex-wrap: wrap; align-items: flex-end; }}
    label {{ display:block; font-size: 13px; color:#595959; margin: 6px 0 4px; }}
    input[type=text], input[type=number] {{ padding: 8px 10px; border:1px solid #d9d9d9; border-radius:4px; min-width: 240px; }}
    button.btn {{ padding: 8px 16px; background:#1677ff; color:#fff; border:none; border-radius:4px; cursor:pointer; }}
    button.btn:disabled {{ background:#bfbfbf; cursor:not-allowed; }}
    table {{ width:100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; }}
    th, td {{ border:1px solid #f0f0f0; padding: 10px 12px; text-align:left; }}
    th {{ background:#fafafa; }}
    .muted {{ color:#8c8c8c; font-size: 13px; }}
    #toast {{ position: fixed; top: 64px; right: 24px; min-width: 220px; display:none; padding: 10px 12px; border-radius: 6px; border: 1px solid #d9d9d9; background:#fff; box-shadow:0 2px 10px rgba(0,0,0,.08); }}
    #toast[data-visible="1"] {{ display:block; }}
    #toast[data-status="success"] {{ border-color:#52c41a; }}
    #toast[data-status="error"] {{ border-color:#ff7875; }}
    #result {{ margin-top: 12px; padding: 12px; border:1px solid #d9d9d9; border-radius: 6px; min-height: 44px; }}
    #result[data-status="success"] {{ border-color:#52c41a; background:#f6ffed; }}
    #result[data-status="error"] {{ border-color:#ff7875; background:#fff2f0; }}
    /* Drawer */
    #drawer {{ position: fixed; top:0; right:0; width: 420px; height: 100vh; background:#fff; border-left: 1px solid #e8e8e8; box-shadow:-2px 0 12px rgba(0,0,0,.08); display:none; padding: 16px 16px 24px; }}
    #drawer[data-visible="1"] {{ display:block; }}
    .drawer-head {{ display:flex; justify-content: space-between; align-items:center; margin-bottom: 8px; }}
    .drawer-title {{ font-size: 16px; font-weight: 600; }}
    .drawer-close {{ border:none; background:transparent; font-size: 18px; cursor:pointer; }}
    .kv {{ margin-top: 10px; font-size: 14px; }}
    .kv strong {{ display:inline-block; width: 120px; color:#595959; }}
  </style>
</head>
<body
  data-testid="inventory-adjust-root"
  data-session-sku="{sku_e}"
  data-old-inventory="{oi}"
  data-failure-mode="{html.escape(fm)}"
>
  <header class="topbar" data-testid="inventory-topbar">
    Commerce 后台 · 库存中心 <span style="margin-left:8px;font-size:12px;color:#fff;opacity:.85;">SANDBOX</span>
  </header>
  <div class="layout">
    <aside class="sider" data-testid="inventory-sider">
      <span style="padding:0 16px;font-size:12px;color:#999;">库存中心</span>
      <a href="/api/v1/internal/rpa-sandbox/admin-like/inventory" data-testid="nav-inv-home">概览</a>
      <a href="/api/v1/internal/rpa-sandbox/admin-like/inventory/adjust" data-testid="nav-inv-adjust">库存调整</a>
    </aside>
    <main class="content">
      <div class="breadcrumb" data-testid="inventory-breadcrumb">首页 / 库存中心 / 库存调整</div>
      <div class="panel">
        <h1 style="margin:0 0 8px;font-size:18px;">库存调整（工作台）</h1>
        <p class="muted" data-testid="inventory-hint">受控页面：用于验证页面导航、列表检索、抽屉编辑与提交回显（非生产）</p>
        <div class="row" data-testid="inventory-search-row">
          <div>
            <label for="sku-search">SKU</label>
            <input type="text" id="sku-search" data-testid="inv-sku-search" value="{sku_e}" autocomplete="off"/>
          </div>
          <div>
            <label for="warehouse">仓库</label>
            <input type="text" id="warehouse" data-testid="inv-warehouse" value="MAIN" readonly/>
          </div>
          <div>
            <button type="button" class="btn" id="search-btn" data-testid="inv-search-btn">查询</button>
          </div>
        </div>
        <div id="list-empty" data-testid="inv-list-empty" style="display:none;margin-top:12px;color:#a8071a;">未找到匹配 SKU</div>
        <div id="list-wrap" data-testid="inv-list-wrap" style="display:none;">
          <table data-testid="inv-table">
            <thead><tr><th>SKU</th><th>写前库存</th><th>操作</th></tr></thead>
            <tbody>
              <tr data-testid="inv-row" data-sku="{sku_e}">
                <td>{sku_e}</td>
                <td data-testid="inv-old">{oi}</td>
                <td><button type="button" class="btn" id="open-drawer" data-testid="inv-open-drawer">调整</button></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div id="result" data-testid="inv-result" data-status="">操作结果将显示在此处</div>
      </div>
    </main>
  </div>

  <div id="toast" data-testid="inv-toast" data-visible="0" data-status="">
    <strong data-testid="inv-toast-title">提示</strong>
    <div data-testid="inv-toast-msg">-</div>
  </div>

  <div id="drawer" data-testid="inventory-adjust-drawer" data-visible="{drawer_visible}">
    <div class="drawer-head">
      <div class="drawer-title" data-testid="inv-drawer-title">调整库存</div>
      <button class="drawer-close" type="button" id="drawer-close" aria-label="close">×</button>
    </div>
    <div class="kv"><strong>SKU</strong><span data-testid="inv-drawer-sku">{sku_e}</span></div>
    <div class="kv"><strong>写前库存</strong><span data-testid="inv-drawer-old">{oi}</span></div>
    <div class="row" style="margin-top: 10px;">
      <div>
        <label for="delta">delta</label>
        <input type="number" id="delta" data-testid="inv-delta" value="{d}"/>
      </div>
      <div>
        <label for="target">target_inventory</label>
        <input type="number" id="target" data-testid="inv-target" value="{ti}"/>
      </div>
    </div>
    <div style="margin-top:12px;">
      <button type="button" class="btn" id="submit-btn" data-testid="inv-submit-btn">提交调整</button>
    </div>
  </div>

  <script>
    (function () {{
      var mode = document.body.getAttribute("data-failure-mode") || "none";
      var sessionSku = (document.body.getAttribute("data-session-sku") || "").trim().toUpperCase();
      var oldInv = parseInt(document.body.getAttribute("data-old-inventory") || "0", 10);
      var searchBtn = document.getElementById("search-btn");
      var skuInput = document.getElementById("sku-search");
      var listWrap = document.getElementById("list-wrap");
      var empty = document.getElementById("list-empty");
      var openDrawerBtn = document.getElementById("open-drawer");
      var drawer = document.getElementById("drawer");
      var closeBtn = document.getElementById("drawer-close");
      var deltaEl = document.getElementById("delta");
      var targetEl = document.getElementById("target");
      var submitBtn = document.getElementById("submit-btn");
      var result = document.getElementById("result");
      var toast = document.getElementById("toast");
      var toastMsg = document.querySelector("[data-testid=inv-toast-msg]");

      function showToast(st, msg) {{
        toast.setAttribute("data-visible", "1");
        toast.setAttribute("data-status", st || "");
        toastMsg.textContent = msg || "";
        setTimeout(function () {{ toast.setAttribute("data-visible","0"); }}, 1200);
      }}

      searchBtn.addEventListener("click", function () {{
        var q = (skuInput.value || "").trim().toUpperCase();
        empty.style.display = "none";
        listWrap.style.display = "none";
        if (q !== sessionSku) {{
          empty.style.display = "block";
          empty.textContent = "未找到匹配 SKU（受控校验：sku mismatch）";
          return;
        }}
        listWrap.style.display = "block";
        showToast("success", "已命中 SKU: " + q);
      }});

      if (closeBtn) {{
        closeBtn.addEventListener("click", function () {{
          drawer.setAttribute("data-visible", "0");
        }});
      }}

      if (openDrawerBtn) {{
        openDrawerBtn.addEventListener("click", function () {{
          if (mode === "element_missing") {{
            // Simulate drawer missing by never making it visible.
            showToast("error", "抽屉组件缺失（受控失败：element_missing）");
            return;
          }}
          drawer.setAttribute("data-visible", "1");
        }});
      }}

      if (submitBtn) {{
        submitBtn.addEventListener("click", function () {{
          var d = parseInt(deltaEl.value || "0", 10);
          var t = parseInt(targetEl.value || "0", 10);
          var newInv = isNaN(t) || t === 0 ? (oldInv + d) : t;
          if (mode === "page_timeout") {{
            // Simulate never returning any result.
            showToast("error", "页面无响应（受控失败：page_timeout）");
            return;
          }}
          result.setAttribute("data-status", "success");
          result.setAttribute("data-old-inventory", String(oldInv));
          result.setAttribute("data-new-inventory", String(newInv));
          result.textContent = "提交成功：库存已更新（受控回显） new_inventory=" + newInv;
          showToast("success", "提交成功");
          drawer.setAttribute("data-visible", "0");
        }});
      }}
    }})();
  </script>
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


@router.get("/catalog", include_in_schema=False, response_class=HTMLResponse)
def admin_like_catalog_page(
    sku: str = Query(default="A001"),
    current_price: float = Query(default=59.9),
    target_price: float = Query(default=39.9),
    failure_mode: str = Query(default="none"),
):
    """Product list (P3.3): search, table, link to detail — internal RPA only."""
    if not settings.ENABLE_INTERNAL_SANDBOX_API:
        raise HTTPException(status_code=503, detail="internal sandbox api disabled")

    fm = _norm_list_detail_failure_mode(failure_mode)
    sku_u = sku.strip().upper()[:64]
    sku_e = html.escape(sku_u)
    cf = float(current_price)
    tf = float(target_price)
    q_detail = urlencode(
        {
            "sku": sku_u,
            "current_price": f"{cf:.4f}",
            "target_price": f"{tf:.4f}",
            "failure_mode": fm,
            "broken": "1" if fm == "detail_page_not_found" else "0",
        }
    )
    detail_href = html.escape(f"/api/v1/internal/rpa-sandbox/admin-like/product-detail?{q_detail}")

    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Commerce 后台 · 商品列表</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: system-ui, sans-serif; background: #f0f2f5; }}
    .topbar {{
      height: 48px; background: #001529; color: #fff; display: flex; align-items: center;
      padding: 0 16px; font-size: 15px; font-weight: 600;
    }}
    .layout {{ display: flex; min-height: calc(100vh - 48px); }}
    .sider {{ width: 200px; background: #fff; border-right: 1px solid #e8e8e8; padding: 12px 0; }}
    .sider span {{ padding: 0 16px; font-size: 12px; color: #999; }}
    .content {{ flex: 1; padding: 20px 24px; }}
    .panel {{
      background: #fff; border-radius: 8px; padding: 16px 20px;
      box-shadow: 0 1px 2px rgba(0,0,0,.06);
    }}
    h1 {{ margin: 0 0 12px; font-size: 18px; }}
    .toolbar {{ display: flex; gap: 8px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }}
    input.search {{ padding: 8px 10px; width: 220px; border: 1px solid #d9d9d9; border-radius: 4px; }}
    button.btn {{
      padding: 8px 16px; background: #1677ff; color: #fff; border: none; border-radius: 4px;
      cursor: pointer; font-size: 14px;
    }}
    .meta {{ font-size: 13px; color: #8c8c8c; margin-bottom: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border: 1px solid #f0f0f0; padding: 10px 12px; text-align: left; }}
    th {{ background: #fafafa; }}
    tbody tr:hover {{ background: #fafafa; }}
    #list-empty {{
      display: none; padding: 24px; text-align: center; color: #a8071a;
      background: #fff2f0; border: 1px solid #ffccc7; border-radius: 4px; margin-top: 8px;
    }}
    #list-empty[data-visible="1"] {{ display: block; }}
    #catalog-table-wrap {{ display: none; }}
    #catalog-table-wrap[data-visible="1"] {{ display: block; }}
    a.row-link {{ color: #1677ff; text-decoration: none; }}
    a.row-link:hover {{ text-decoration: underline; }}
  </style>
</head>
<body data-testid="catalog-root" data-session-sku="{sku_e}" data-failure-mode="{html.escape(fm)}">
  <header class="topbar" data-testid="catalog-topbar">Commerce 后台 · 商品中心</header>
  <div class="layout">
    <aside class="sider"><span>导航</span></aside>
    <main class="content">
      <div class="panel">
        <h1>商品列表</h1>
        <p class="meta" data-testid="list-result-hint">共 <span id="result-count">0</span> 条（受控环境）</p>
        <div class="toolbar">
          <label for="catalog-search">SKU</label>
          <input type="text" id="catalog-search" class="search" data-testid="catalog-search" value="{sku_e}" autocomplete="off"/>
          <button type="button" class="btn" id="catalog-search-btn" data-testid="catalog-search-btn">搜索</button>
        </div>
        <div id="list-empty" data-testid="list-empty" data-visible="0">未找到匹配商品（列表为空）</div>
        <div id="catalog-table-wrap" data-visible="0">
          <table data-testid="catalog-table">
            <thead><tr><th>SKU</th><th>商品名</th><th>价格</th><th>操作</th></tr></thead>
            <tbody id="catalog-tbody">
              <tr data-testid="product-row" data-sku="{sku_e}" style="display:none;">
                <td>{sku_e}</td>
                <td>受控示例商品</td>
                <td data-testid="row-price">{cf:.2f}</td>
                <td><a class="row-link" data-testid="open-product-detail" href="{detail_href}">编辑</a></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </main>
  </div>
  <script>
    (function () {{
      var body = document.body;
      var mode = body.getAttribute("data-failure-mode") || "none";
      var sessionSku = (body.getAttribute("data-session-sku") || "").trim().toUpperCase();
      var inp = document.getElementById("catalog-search");
      var btn = document.getElementById("catalog-search-btn");
      var empty = document.getElementById("list-empty");
      var wrap = document.getElementById("catalog-table-wrap");
      var countEl = document.getElementById("result-count");
      var row = document.querySelector("[data-testid=product-row]");

      function runSearch() {{
        var q = (inp.value || "").trim().toUpperCase();
        empty.setAttribute("data-visible", "0");
        wrap.setAttribute("data-visible", "0");
        row.style.display = "none";
        countEl.textContent = "0";

        if (mode === "sku_missing_in_list") {{
          empty.setAttribute("data-visible", "1");
          empty.textContent = "未找到匹配商品（受控失败：sku_missing_in_list）";
          return;
        }}
        if (q !== sessionSku) {{
          empty.setAttribute("data-visible", "1");
          empty.textContent = "搜索无结果：SKU 与当前任务不一致";
          return;
        }}
        row.style.display = "table-row";
        wrap.setAttribute("data-visible", "1");
        countEl.textContent = "1";
      }}
      btn.addEventListener("click", runSearch);
    }})();
  </script>
</body>
</html>"""
    return HTMLResponse(content=page)


@router.get("/product-detail", include_in_schema=False, response_class=HTMLResponse)
def admin_like_product_detail_page(
    sku: str = Query(default="A001"),
    current_price: float = Query(default=59.9),
    target_price: float = Query(default=39.9),
    failure_mode: str = Query(default="none"),
    broken: int = Query(default=0, ge=0, le=1),
):
    """Detail / edit (P3.3); broken=1 simulates detail not loading."""
    if not settings.ENABLE_INTERNAL_SANDBOX_API:
        raise HTTPException(status_code=503, detail="internal sandbox api disabled")

    fm = _norm_list_detail_failure_mode(failure_mode)
    sku_u = sku.strip().upper()[:64]
    sku_e = html.escape(sku_u)
    cf = float(current_price)
    tf = float(target_price)
    save_dis = fm == "save_button_disabled"

    if broken:
        return HTMLResponse(
            content=f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/><title>404</title></head>
<body data-testid="detail-not-found" style="font-family:system-ui;padding:2rem;">
  <h1>页面无法打开</h1>
  <p data-testid="detail-error-msg">商品详情不存在或已删除（受控失败：detail_page_not_found）</p>
  <p>SKU: {sku_e}</p>
</body></html>"""
        )

    save_attr = "disabled" if save_dis else ""
    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>商品详情 · 编辑</title>
  <style>
    body {{ margin: 0; font-family: system-ui, sans-serif; background: #f0f2f5; }}
    .topbar {{ height: 48px; background: #001529; color: #fff; display: flex; align-items: center; padding: 0 16px; font-weight: 600; }}
    .wrap {{ max-width: 720px; margin: 20px auto; padding: 0 16px; }}
    .panel {{
      background: #fff; border-radius: 8px; padding: 24px;
      box-shadow: 0 1px 2px rgba(0,0,0,.06);
    }}
    h1 {{ margin: 0 0 8px; font-size: 20px; }}
    .breadcrumb {{ font-size: 12px; color: #8c8c8c; margin-bottom: 16px; }}
    .field {{ margin: 12px 0; font-size: 14px; }}
    .field label {{ display: block; color: #595959; margin-bottom: 4px; }}
    .field input {{ width: 100%; max-width: 280px; padding: 8px 10px; border: 1px solid #d9d9d9; border-radius: 4px; }}
    button.save {{
      margin-top: 16px; padding: 8px 24px; background: #1677ff; color: #fff; border: none;
      border-radius: 4px; cursor: pointer; font-size: 14px;
    }}
    button.save:disabled {{ background: #bfbfbf; cursor: not-allowed; }}
    #detail-result {{
      margin-top: 20px; padding: 12px; border: 1px solid #d9d9d9; border-radius: 4px; min-height: 48px;
      font-size: 14px;
    }}
    #detail-result[data-status="error"] {{ border-color: #ff7875; background: #fff2f0; }}
    #detail-result[data-status="success"] {{ border-color: #52c41a; background: #f6ffed; }}
    .card-head {{ font-size: 16px; font-weight: 600; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #f0f0f0; }}
  </style>
</head>
<body
  data-testid="detail-product-root"
  data-failure-mode="{html.escape(fm)}"
  data-sku="{sku_e}"
  data-current-price="{cf:.4f}"
>
  <header class="topbar" data-testid="detail-topbar">Commerce 后台</header>
  <div class="wrap">
    <div class="breadcrumb" data-testid="detail-breadcrumb">商品 / 列表 / 详情编辑</div>
    <div class="panel">
      <h1 data-testid="detail-title">商品详情</h1>
      <div class="card-head">基本信息</div>
      <div class="field"><label>SKU</label><div data-testid="detail-sku-display">{sku_e}</div></div>
      <div class="field"><label>当前价格</label><div data-testid="detail-current-price">{cf:.2f}</div></div>
      <div class="field">
        <label for="detail-new-price">新价格</label>
        <input type="number" step="0.01" id="detail-new-price" data-testid="detail-new-price" value="{tf:.2f}"/>
      </div>
      <button type="button" class="save" id="detail-save-btn" data-testid="detail-save-btn" {save_attr}>保存更改</button>
      <div id="detail-result" data-testid="detail-result" data-status="" data-page-status="">保存后将显示操作结果</div>
    </div>
  </div>
  <script>
    (function () {{
      var mode = document.body.getAttribute("data-failure-mode") || "none";
      var cur = parseFloat(document.body.getAttribute("data-current-price") || "0");
      var newp = document.getElementById("detail-new-price");
      var save = document.getElementById("detail-save-btn");
      var out = document.getElementById("detail-result");

      save.addEventListener("click", function () {{
        if (save.disabled) {{
          out.setAttribute("data-status", "error");
          out.setAttribute("data-page-status", "error");
          out.textContent = "保存按钮不可用（受控失败：save_button_disabled）";
          return;
        }}
        var v = parseFloat(newp.value);
        if (isNaN(v)) {{
          out.setAttribute("data-status", "error");
          out.setAttribute("data-page-status", "error");
          out.textContent = "价格无效";
          return;
        }}
        if (mode === "save_error") {{
          out.setAttribute("data-status", "error");
          out.setAttribute("data-page-status", "error");
          out.textContent = "保存失败：后台拒绝（受控失败：save_error）";
          return;
        }}
        out.setAttribute("data-status", "success");
        out.setAttribute("data-page-status", "success");
        out.setAttribute("data-old-price", String(cur));
        out.setAttribute("data-new-price", String(v));
        out.setAttribute("data-operation-result", "saved");
        out.textContent = "保存成功，新价格：" + v;
      }});
    }})();
  </script>
</body>
</html>"""
    return HTMLResponse(content=page)
