import lark_oapi as lark
from app.core.config import settings

# 测试客户端方法
print("Testing Client methods...")

client = lark.Client()
print(f"Client methods: {[method for method in dir(client) if not method.startswith('_')]}")

# 检查是否有设置 app_id 和 app_secret 的方法
try:
    print("\nTesting client configuration...")
    if hasattr(client, 'app_id'):
        client.app_id = settings.FEISHU_APP_ID
        print("   Set app_id successfully")
    if hasattr(client, 'app_secret'):
        client.app_secret = settings.FEISHU_APP_SECRET
        print("   Set app_secret successfully")
    if hasattr(client, 'log_level'):
        client.log_level = lark.LogLevel.DEBUG
        print("   Set log_level successfully")
    print("   Client configured successfully")
except Exception as e:
    print(f"   Error: {e}")

# 检查 im 服务是否可用
try:
    print("\nTesting im service...")
    if hasattr(client, 'im'):
        print("   im service found")
        if hasattr(client.im, 'message'):
            print("   message service found")
            if hasattr(client.im.message, 'reply'):
                print("   reply method found")
except Exception as e:
    print(f"   Error: {e}")