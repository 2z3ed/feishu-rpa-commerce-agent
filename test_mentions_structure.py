import json

# 模拟真实的群聊 payload
sample_payload = {
    "schema": "2.0",
    "header": {
        "event_id": "test_event_id",
        "token": "",
        "create_time": "1775648731434",
        "event_type": "im.message.receive_v1",
        "tenant_key": "test_tenant",
        "app_id": "cli_a95f7e3bbcfcdbcb"
    },
    "event": {
        "message": {
            "chat_id": "oc_778470ab02432d4ae96d7c8241814985",
            "chat_type": "group",
            "content": "{\"text\":\"@_user_1 测试\"}",
            "create_time": "1775648731024",
            "mentions": [
                {
                    "bot_info": {
                        "app_id": "cli_a95f7e3bbcfcdbcb"
                    },
                    "id": {
                        "open_id": "ou_19c10349af5d0eea7a6c556d574ed737",
                        "union_id": "on_189470feaaae79df6845e0572df2f1c3",
                        "user_id": None
                    },
                    "key": "@_user_1",
                    "mentioned_type": "bot",
                    "name": "电商后台全链路RPA自动化平台",
                    "tenant_key": "1aac760ded1b1c91"
                }
            ],
            "message_id": "om_x100b5257b363c4acb2e45c968f64e0a",
            "message_type": "text",
            "update_time": "1775648731128"
        },
        "sender": {
            "sender_id": {
                "open_id": "ou_cc5ce556aeae9de47ef7f43b307f5661",
                "union_id": "on_52b8e1c502c939798408b7921aad4e95",
                "user_id": None
            },
            "sender_type": "user",
            "tenant_key": "1aac760ded1b1c91"
        }
    }
}

print("Sample mentions structure:")
print(json.dumps(sample_payload['event']['message']['mentions'], indent=2, ensure_ascii=False))

print("\nMention structure:")
mention = sample_payload['event']['message']['mentions'][0]
print(f"  mentioned_type: {mention.get('mentioned_type')}")
print(f"  bot_info: {mention.get('bot_info')}")
print(f"  bot_info.app_id: {mention.get('bot_info', {}).get('app_id')}")