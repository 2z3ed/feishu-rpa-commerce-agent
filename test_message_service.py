import lark_oapi as lark
from app.core.config import settings

# 初始化客户端
client = lark.Client().builder()\
    .app_id(settings.FEISHU_APP_ID)\
    .app_secret(settings.FEISHU_APP_SECRET)\
    .log_level(lark.LogLevel.DEBUG)\
    .build()

print("=== Checking client.im.v1.message structure ===")
print(f"client.im.v1.message type: {type(client.im.v1.message)}")
print(f"client.im.v1.message attributes: {[attr for attr in dir(client.im.v1.message) if not attr.startswith('_')]}")

# 检查 reply 方法
if hasattr(client.im.v1.message, 'reply'):
    print("\n✓ reply method found!")
    print(f"  reply method: {client.im.v1.message.reply}")

# 检查 create 方法
if hasattr(client.im.v1.message, 'create'):
    print("\n✓ create method found!")
    print(f"  create method: {client.im.v1.message.create}")