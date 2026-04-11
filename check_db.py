import sqlite3

# 连接到 SQLite 数据库
conn = sqlite3.connect('feishu_rpa.db')
cursor = conn.cursor()

print("=== 检查数据库表 ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for table in tables:
    print(f"表: {table[0]}")

print("\n=== message_idempotency 表数据 ===")
try:
    cursor.execute("SELECT * FROM message_idempotency ORDER BY created_at DESC LIMIT 5;")
    rows = cursor.fetchall()
    print(f"找到 {len(rows)} 条记录")
    for row in rows:
        print(row)
except Exception as e:
    print(f"查询 message_idempotency 表时出错: {e}")

print("\n=== task_records 表数据 ===")
try:
    cursor.execute("SELECT * FROM task_records ORDER BY created_at DESC LIMIT 5;")
    rows = cursor.fetchall()
    print(f"找到 {len(rows)} 条记录")
    for row in rows:
        print(row)
except Exception as e:
    print(f"查询 task_records 表时出错: {e}")

# 关闭连接
conn.close()