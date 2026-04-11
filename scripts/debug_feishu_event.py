#!/usr/bin/env python3
"""
本地调试脚本：模拟飞书消息事件，验证整个后端处理链路

用途：
- 验证 parser 能正确解析飞书事件
- 验证 idempotency 服务能正确创建/检查记录
- 验证 task_records 能正确创建
- 验证 Celery 任务能正确入队
- 验证飞书回执能正确发送

使用：
    python scripts/debug_feishu_event.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.feishu.parser import parse_p2_im_message_receive_v1
from app.services.feishu.idempotency import idempotency_service
from app.services.feishu.client import feishu_client
from app.tasks.ingress_tasks import process_ingress_message
from app.core.logging import logger


MOCK_FEISHU_EVENT = {
    "header": {
        "event_id": "evt_abc123",
        "token": "test_token",
        "create_time": "1704067200000",
        "event_type": "im.message.receive_v1",
        "app_id": "cli_a95f7e3bbcfcdbcb",
        "tenant_key": "test_tenant"
    },
    "event": {
        "message": {
            "message_id": "om_test_msg_123456",
            "chat_id": "oc_test_chat_789",
            "chat_type": "group",
            "msg_type": "text",
            "root_id": "",
            "parent_id": "",
            "create_time": "1704067200000",
            "sender": {
                "sender_id": {
                    "open_id": "ou_test_user_abc",
                    "union_id": "un_test_union",
                    "user_id": "ui_test_user"
                },
                "sender_type": "user",
                "tenant_key": "test_tenant"
            },
            "body": {
                "content": "测试一下看能否收到消息"
            },
            "mentions": []
        },
        "sender": {
            "sender_id": {
                "open_id": "ou_test_user_abc",
                "union_id": "un_test_union",
                "user_id": "ui_test_user"
            },
            "sender_type": "user",
            "tenant_key": "test_tenant"
        }
    }
}


def mock_p2_event():
    """创建模拟的 P2ImMessageReceiveV1 对象"""
    from dataclasses import dataclass, field
    from typing import Optional, Dict, Any
    
    @dataclass
    class MockMessage:
        message_id: str = "om_test_msg_123456"
        chat_id: str = "oc_test_chat_789"
        msg_type: str = "text"
        create_time: str = "1704067200000"
        
        @property
        def body(self):
            @dataclass
            class MockBody:
                content: str = "测试一下看能否收到消息"
            return MockBody()
    
    @dataclass
    class MockSenderId:
        open_id: str = "ou_test_user_abc"
        user_id: str = "ui_test_user"
    
    @dataclass
    class MockSender:
        sender_id: MockSenderId = field(default_factory=MockSenderId)
    
    @dataclass
    class MockEvent:
        message: MockMessage = field(default_factory=MockMessage)
        sender: MockSender = field(default_factory=MockSender)
    
    @dataclass
    class MockFullEvent:
        event: MockEvent = field(default_factory=MockEvent)
        header: Dict[str, Any] = field(default_factory=lambda: {
            "event_id": "evt_abc123",
            "event_type": "im.message.receive_v1"
        })
        
        def to_dict(self):
            return {
                "event": {
                    "message": {
                        "message_id": self.event.message.message_id,
                        "chat_id": self.event.message.chat_id,
                        "msg_type": self.event.message.msg_type,
                        "create_time": self.event.message.create_time,
                        "body": {
                            "content": self.event.message.body.content
                        }
                    },
                    "sender": {
                        "sender_id": {
                            "open_id": self.event.sender.sender_id.open_id,
                            "user_id": self.event.sender.sender_id.user_id
                        }
                    }
                },
                "header": self.header
            }
    
    return MockFullEvent()


def main():
    print("=" * 60)
    print("开始本地调试：模拟飞书消息事件")
    print("=" * 60)
    
    logger.info("=== DEBUG SCRIPT STARTED ===")
    
    print("\n[1/5] 解析飞书事件...")
    mock_event = mock_p2_event()
    message_event = parse_p2_im_message_receive_v1(mock_event)
    
    if not message_event:
        print("❌ Parser 返回 None，检查日志看原因")
        return False
    
    print(f"✅ Parser 成功: message_id={message_event.message_id}, text={message_event.text[:30]}...")
    
    print("\n[2/5] 幂等检查...")
    payload = {
        "message_id": message_event.message_id,
        "chat_id": message_event.chat_id,
        "open_id": message_event.open_id,
        "text": message_event.text,
        "create_time": message_event.create_time,
    }
    
    is_duplicate, existing_task_id, new_task_id = idempotency_service.check_and_create(
        message_id=message_event.message_id,
        raw_payload=payload
    )
    
    if is_duplicate:
        print(f"⚠️  幂等命中，已存在 task_id={existing_task_id}")
    else:
        print(f"✅ 幂等通过，创建新 task_id={new_task_id}")
    
    if not new_task_id:
        print("❌ 创建 task_id 失败")
        return False
    
    print("\n[3/5] Celery 任务入队...")
    try:
        task = process_ingress_message.delay(new_task_id, message_event.text, message_event.open_id)
        print(f"✅ Celery 入队成功: celery_task_id={task.id}")
    except Exception as e:
        print(f"❌ Celery 入队失败: {e}")
        return False
    
    print("\n[4/5] 发送飞书回执...")
    try:
        response_text = f"已接收任务，任务号：{new_task_id}\n当前状态：queued"
        reply_success = feishu_client.send_text_reply(
            message_id=message_event.message_id,
            text=response_text
        )
        if reply_success:
            print(f"✅ 飞书回执发送成功")
        else:
            print(f"⚠️ 飞书回执发送失败（message_id 可能无效，这是预期的）")
    except Exception as e:
        print(f"⚠️ 飞书回执异常（可能因为 mock message_id 无效）: {e}")
    
    print("\n[5/5] 检查数据库...")
    from app.db.session import SessionLocal
    from app.db.models import TaskRecord, MessageIdempotency
    
    db = SessionLocal()
    try:
        task_record = db.query(TaskRecord).filter(TaskRecord.task_id == new_task_id).first()
        if task_record:
            print(f"✅ task_records 表有记录: task_id={task_record.task_id}, status={task_record.status}")
        else:
            print("❌ task_records 表没有记录")
        
        idempotency = db.query(MessageIdempotency).filter(
            MessageIdempotency.message_id == message_event.message_id
        ).first()
        if idempotency:
            print(f"✅ message_idempotency 表有记录: message_id={idempotency.message_id}, task_id={idempotency.task_id}")
        else:
            print("❌ message_idempotency 表没有记录")
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("本地调试完成！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)