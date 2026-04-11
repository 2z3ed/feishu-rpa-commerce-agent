import lark_oapi as lark
from app.core.config import settings

# 初始化客户端
client = lark.Client().builder()\
    .app_id(settings.FEISHU_APP_ID)\
    .app_secret(settings.FEISHU_APP_SECRET)\
    .log_level(lark.LogLevel.DEBUG)\
    .build()

print("=== Checking client.im structure ===")
print(f"client.im type: {type(client.im)}")
print(f"client.im attributes: {[attr for attr in dir(client.im) if not attr.startswith('_')]}")

# 检查是否有 message 相关的方法
print("\n=== Looking for message-related methods ===")
for attr in dir(client.im):
    if not attr.startswith('_'):
        print(f"  - {attr}")
        obj = getattr(client.im, attr)
        if hasattr(obj, '__call__'):
            print(f"    (callable)")
        elif hasattr(obj, '__dict__'):
            print(f"    (object with attributes: {[a for a in dir(obj) if not a.startswith('_')]})")