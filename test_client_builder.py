import lark_oapi as lark
from app.core.config import settings

# 测试 builder 方法
print("Testing builder method...")

client = lark.Client()

if hasattr(client, 'builder'):
    print("Builder method found")
    builder = client.builder()
    print(f"Builder methods: {[method for method in dir(builder) if not method.startswith('_')]}")
    
    # 尝试使用 builder 配置
    try:
        # 尝试不同的方法名
        if hasattr(builder, 'app_id'):
            builder = builder.app_id(settings.FEISHU_APP_ID)
            print("Set app_id")
        elif hasattr(builder, 'with_app_id'):
            builder = builder.with_app_id(settings.FEISHU_APP_ID)
            print("Set app_id with with_app_id")
        
        if hasattr(builder, 'app_secret'):
            builder = builder.app_secret(settings.FEISHU_APP_SECRET)
            print("Set app_secret")
        elif hasattr(builder, 'with_app_secret'):
            builder = builder.with_app_secret(settings.FEISHU_APP_SECRET)
            print("Set app_secret with with_app_secret")
        
        if hasattr(builder, 'log_level'):
            builder = builder.log_level(lark.LogLevel.DEBUG)
            print("Set log_level")
        elif hasattr(builder, 'with_log_level'):
            builder = builder.with_log_level(lark.LogLevel.DEBUG)
            print("Set log_level with with_log_level")
        
        if hasattr(builder, 'build'):
            new_client = builder.build()
            print("Client built successfully")
            print(f"New client has im service: {hasattr(new_client, 'im')}")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Builder method not found")