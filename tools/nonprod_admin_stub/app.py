from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "nonprod_stub.db"
SESSION_COOKIE = "nonprod_stub_session"
SESSION_VALUE = "admin-session"
LOGIN_USER = "admin"
LOGIN_PASSWORD = "admin123"
DEFAULT_WAREHOUSE = "MAIN"

FAIL_MODE = (os.getenv("NONPROD_FAIL_MODE") or "").strip().lower()
PORT = int(os.getenv("NONPROD_ADMIN_STUB_PORT") or "18081")

app = FastAPI(title="nonprod-admin-stub", version="0.1.0")


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS inventory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL UNIQUE,
    warehouse TEXT NOT NULL,
    inventory INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect_db() -> Iterator[sqlite3.Connection]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect_db() as conn:
        conn.execute(SCHEMA_SQL)
        row = conn.execute("SELECT COUNT(*) AS c FROM inventory_items").fetchone()
        if int(row["c"] or 0) == 0:
            conn.execute(
                "INSERT INTO inventory_items (sku, warehouse, inventory, updated_at) VALUES (?, ?, ?, ?)",
                ("A001", DEFAULT_WAREHOUSE, 100, _now()),
            )


def is_logged_in(request: Request) -> bool:
    return request.cookies.get(SESSION_COOKIE) == SESSION_VALUE


def render_page(title: str, body: str) -> HTMLResponse:
    html = f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 0; background: #f7f7fb; color: #111; }}
    .shell {{ display: grid; grid-template-columns: 220px 1fr; min-height: 100vh; }}
    .sidebar {{ background: #101828; color: #fff; padding: 24px; }}
    .sidebar a {{ color: #d0d5dd; text-decoration: none; display: block; margin: 10px 0; }}
    .main {{ padding: 28px; }}
    .card {{ background: #fff; border-radius: 16px; padding: 20px; box-shadow: 0 8px 30px rgba(16,24,40,.08); margin-bottom: 16px; }}
    label {{ display:block; margin: 12px 0 6px; }}
    input {{ padding: 10px 12px; width: 100%; max-width: 420px; box-sizing: border-box; }}
    button {{ padding: 10px 14px; margin-top: 12px; cursor: pointer; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ border-bottom: 1px solid #e4e7ec; text-align: left; padding: 10px 8px; }}
    .msg-ok {{ color: #067647; }}
    .msg-err {{ color: #b42318; }}
    .hint {{ color: #667085; font-size: 14px; }}
  </style>
</head>
<body>
{body}
</body>
</html>"""
    return HTMLResponse(content=html)


def login_required_html(next_path: str) -> HTMLResponse:
    body = f"""<div class=\"shell\"><aside class=\"sidebar\"><h2>Nonprod Admin</h2></aside><main class=\"main\"><div class=\"card\"><h1>未登录</h1><p>请先登录后访问后台。</p><a href=\"/login?next={next_path}\">去登录</a></div></main></div>"""
    return render_page("未登录", body)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "nonprod-admin-stub"}


@app.get("/login")
def login_page(next: str = "/admin") -> HTMLResponse:
    body = f"""<div class=\"shell\"><aside class=\"sidebar\"><h2>Nonprod Admin</h2><p class=\"hint\">stub login</p></aside><main class=\"main\"><div class=\"card\"><h1>登录</h1><form method=\"post\" action=\"/login\"><input type=\"hidden\" name=\"next\" value=\"{next}\" /><label>用户名</label><input name=\"username\" value=\"admin\" /><label>密码</label><input name=\"password\" type=\"password\" value=\"admin123\" /><button type=\"submit\">登录</button></form></div></main></div>"""
    return render_page("登录", body)


@app.post("/login")
async def login(request: Request):
    from urllib.parse import parse_qs

    raw = (await request.body()).decode("utf-8", errors="ignore")
    form = {k: (v[0] if v else "") for k, v in parse_qs(raw, keep_blank_values=True).items()}
    username = str(form.get("username") or "")
    password = str(form.get("password") or "")
    next_path = str(form.get("next") or "/admin")
    if username != LOGIN_USER or password != LOGIN_PASSWORD:
        body = f"""<div class=\"shell\"><aside class=\"sidebar\"><h2>Nonprod Admin</h2></aside><main class=\"main\"><div class=\"card\"><h1 class=\"msg-err\">登录失败</h1><p>账号或密码错误。</p><a href=\"/login?next={next_path}\">返回登录</a></div></main></div>"""
        return render_page("登录失败", body)
    resp = RedirectResponse(url=next_path or "/admin", status_code=303)
    resp.set_cookie(SESSION_COOKIE, SESSION_VALUE, httponly=True, samesite="lax")
    return resp


@app.get("/admin")
def admin_home(request: Request) -> HTMLResponse:
    if not is_logged_in(request):
        return login_required_html("/admin")
    body = """<div class="shell"><aside class="sidebar"><h2>Nonprod Admin</h2><a href="/admin">后台首页</a><a href="/admin/inventory">库存中心</a></aside><main class="main"><div class="card"><h1>后台首页</h1><p>已登录：admin</p><p class="hint">使用左侧导航进入库存中心。</p></div></main></div>"""
    return render_page("后台首页", body)


@app.get("/admin/inventory")
def inventory_page(request: Request, sku: str = "") -> HTMLResponse:
    if not is_logged_in(request):
        return login_required_html("/admin/inventory")
    if FAIL_MODE == "entry_not_ready":
        body = """<div class="shell"><aside class="sidebar"><h2>Nonprod Admin</h2><a href="/admin">后台首页</a><a href="/admin/inventory">库存中心</a></aside><main class="main"><div class="card"><h1 class="msg-err">入口未就绪</h1><p>库存页暂不可用。</p></div></main></div>"""
        return render_page("入口未就绪", body)
    item = None
    if sku:
        with connect_db() as conn:
            item = conn.execute("SELECT * FROM inventory_items WHERE sku = ?", (sku.strip().upper(),)).fetchone()
    result_html = "<p class='hint'>请输入 SKU 后查询。</p>"
    if item:
        adjust_url = f"/admin/inventory/adjust?{urlencode({'sku': item['sku']})}"
        result_html = f"""
        <table>
          <tr><th>SKU</th><td>{item['sku']}</td></tr>
          <tr><th>Warehouse</th><td>{item['warehouse']}</td></tr>
          <tr><th>Current Inventory</th><td>{item['inventory']}</td></tr>
        </table>
        <p><a href="{adjust_url}">调整</a></p>
        """
    body = f"""<div class="shell"><aside class="sidebar"><h2>Nonprod Admin</h2><a href="/admin">后台首页</a><a href="/admin/inventory">库存中心</a></aside><main class="main"><div class="card"><h1>库存中心</h1><form method="get"><label>SKU</label><input name="sku" value="{sku}" placeholder="A001" /><button type="submit">查询</button></form>{result_html}</div></main></div>"""
    return render_page("库存中心", body)


@app.get("/admin/inventory/adjust")
def adjust_page(request: Request, sku: str = "") -> HTMLResponse:
    if not is_logged_in(request):
        return login_required_html(f"/admin/inventory/adjust?{urlencode({'sku': sku})}")
    if FAIL_MODE == "element_missing":
        body = """<div class="shell"><aside class="sidebar"><h2>Nonprod Admin</h2><a href="/admin">后台首页</a><a href="/admin/inventory">库存中心</a></aside><main class="main"><div class="card"><h1 class="msg-err">元素缺失</h1><p>编辑入口暂不可用。</p></div></main></div>"""
        return render_page("元素缺失", body)
    sku_val = sku.strip().upper() or "A001"
    with connect_db() as conn:
        item = conn.execute("SELECT * FROM inventory_items WHERE sku = ?", (sku_val,)).fetchone()
    if not item:
        body = f"""<div class="shell"><aside class="sidebar"><h2>Nonprod Admin</h2><a href="/admin">后台首页</a><a href="/admin/inventory">库存中心</a></aside><main class="main"><div class="card"><h1>库存调整</h1><p class="msg-err">SKU 不存在</p></div></main></div>"""
        return render_page("SKU 不存在", body)
    body = f"""<div class="shell"><aside class="sidebar"><h2>Nonprod Admin</h2><a href="/admin">后台首页</a><a href="/admin/inventory">库存中心</a></aside><main class="main"><div class="card"><h1>库存调整</h1><form method="post" action="/admin/inventory/adjust"><input type="hidden" name="sku" value="{item['sku']}" /><label>SKU</label><input name="sku_display" value="{item['sku']}" readonly /><label>当前库存</label><input name="current_inventory" value="{item['inventory']}" readonly /><label>delta</label><input name="delta" type="number" value="0" /><label>target_inventory</label><input name="target_inventory" type="number" value="{item['inventory']}" /><button type="submit">提交</button></form></div></main></div>"""
    return render_page("库存调整", body)


@app.post("/admin/inventory/adjust")
async def adjust_submit(request: Request):
    if not is_logged_in(request):
        return login_required_html("/admin/inventory/adjust")
    if FAIL_MODE == "session_invalid":
        body = """<div class="shell"><aside class="sidebar"><h2>Nonprod Admin</h2><a href="/admin">后台首页</a><a href="/admin/inventory">库存中心</a></aside><main class="main"><div class="card"><h1 class="msg-err">会话失效</h1><p>请重新登录。</p></div></main></div>"""
        resp = render_page("会话失效", body)
        resp.delete_cookie(SESSION_COOKIE)
        return resp
    from urllib.parse import parse_qs

    raw = (await request.body()).decode("utf-8", errors="ignore")
    form = {k: (v[0] if v else "") for k, v in parse_qs(raw, keep_blank_values=True).items()}
    sku_val = str(form.get("sku") or "").strip().upper()
    delta = int(str(form.get("delta") or "0") or 0)
    target_raw = str(form.get("target_inventory") or "").strip()
    target_inventory = int(target_raw) if target_raw else None
    with connect_db() as conn:
        item = conn.execute("SELECT * FROM inventory_items WHERE sku = ?", (sku_val,)).fetchone()
        if not item:
            body = """<div class="shell"><aside class="sidebar"><h2>Nonprod Admin</h2><a href="/admin">后台首页</a><a href="/admin/inventory">库存中心</a></aside><main class="main"><div class="card"><h1 class="msg-err">提交失败</h1><p>SKU 不存在。</p></div></main></div>"""
            return render_page("提交失败", body)
        current = int(item["inventory"])
        new_inventory = int(target_inventory) if target_inventory is not None else current + int(delta)
        conn.execute(
            "UPDATE inventory_items SET inventory = ?, updated_at = ? WHERE sku = ?",
            (new_inventory, _now(), sku_val),
        )
    body = f"""<div class="shell"><aside class="sidebar"><h2>Nonprod Admin</h2><a href="/admin">后台首页</a><a href="/admin/inventory">库存中心</a></aside><main class="main"><div class="card"><h1 class="msg-ok">提交成功</h1><p>SKU: {sku_val}</p><p>写后库存: {new_inventory}</p><p><a href="/admin/inventory?sku={sku_val}">返回查询</a></p></div></main></div>"""
    return render_page("提交成功", body)


if __name__ == "__main__":
    import uvicorn

    init_db()
    uvicorn.run("tools.nonprod_admin_stub.app:app", host="127.0.0.1", port=PORT, reload=False)
