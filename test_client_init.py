import lark_oapi as lark
from app.core.config import settings

# 尝试不同的初始化方式
print("Testing Client initialization...")

try:
    # 尝试直接初始化
    print("1. Testing direct Client initialization...")
    client = lark.Client()
    print("   Success! Client initialized without parameters")
except Exception as e:
    print(f"   Error: {e}")

try:
    # 尝试使用 builder 模式
    print("\n2. Testing builder pattern...")
    if hasattr(lark, 'ClientBuilder'):
        client = lark.ClientBuilder().app_id(settings.FEISHU_APP_ID).app_secret(settings.FEISHU_APP_SECRET).build()
        print("   Success! Client initialized with builder")
    else:
        print("   ClientBuilder not found")
except Exception as e:
    print(f"   Error: {e}")

try:
    # 检查是否有其他初始化方式
    print("\n3. Checking for other initialization methods...")
    print(f"   lark_oapi has: {[attr for attr in dir(lark) if 'client' in attr.lower() or 'init' in attr.lower()]}")
except Exception as e:
    print(f"   Error: {e}")