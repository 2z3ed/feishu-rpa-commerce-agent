import threading
import time
import json
import sys
import re
from typing import Any

try:
    import lark_oapi as lark
    from lark_oapi import EventDispatcherHandler, LogLevel
except Exception:  # pragma: no cover - fallback for unit tests without full SDK
    lark = None  # type: ignore[assignment]
    EventDispatcherHandler = None  # type: ignore[assignment]
    LogLevel = None  # type: ignore[assignment]

from app.core.config import settings
from app.core.logging import logger
from app.services.feishu.parser import parse_p2_im_message_receive_v1, FeishuMessageEvent
from app.services.feishu.idempotency import idempotency_service
from app.services.feishu.client import feishu_client
from app.core.constants import TaskStatus
from app.db.session import SessionLocal
from app.db.models import TaskRecord
from app.graph.nodes.execute_action import execute_action, _load_latest_discovery_context
from app.clients.b_service_client import BServiceClient
from app.services.feishu.cards.monitor_targets import (
    build_monitor_target_delete_confirm_card,
    build_monitor_targets_card,
)


def _can_mark_task_queued(current_status: str) -> bool:
    normalized = str(current_status or "").strip().lower()
    return normalized in {TaskStatus.RECEIVED.value, TaskStatus.QUEUED.value}


class FeishuLongConnListener:
    @staticmethod
    def _extract_monitor_targets_list(targets_data: dict[str, Any]) -> list[dict]:
        targets = targets_data.get("targets")
        if isinstance(targets, list):
            return [item for item in targets if isinstance(item, dict)]
        items = targets_data.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
        return []

    @staticmethod
    def _find_target_in_list(targets: list[dict], target_id: int) -> tuple[bool, str]:
        for item in targets:
            raw_id = item.get("target_id")
            if raw_id in (None, ""):
                raw_id = item.get("id") or item.get("product_id")
            try:
                if int(raw_id) != int(target_id):
                    continue
            except Exception:
                continue
            status = str(item.get("status") or "").strip().lower() or "unknown"
            return True, status
        return False, "missing"

    def __init__(self):
        self._client = None
        self._running = False
        self._thread = None

    def _handle_message_event(self, data):
        # ===== 绝对入口日志 =====
        print(f"===========================================>", file=sys.stderr)
        print(f">>> ENTER _handle_message_event with data type: {type(data)}", file=sys.stderr)
        print(f"===========================================>", file=sys.stderr)
        
        try:
            # ========== 强制可见调试：收到任意飞书事件 ==========
            logger.info("=== _handle_message_event CALLED === data_type=%s", type(data))
            
            raw_dict = data.to_dict() if hasattr(data, 'to_dict') else {}
            logger.info("=== FEISHU EVENT RECEIVED === event_type=im.message.receive_v1, raw_payload=%s", 
                        json.dumps(raw_dict, ensure_ascii=False)[:500])

            # ========== 解析消息 ==========
            message_event = parse_p2_im_message_receive_v1(data)
            
            # ========== 调试：打印 parser 结果 ==========
            if not message_event:
                logger.warning("=== PARSER RETURNED NONE === message event is None, skipping")
                return

            # ========== 明确打印 message_id 追踪 ==========
            logger.info("=== PARSER SUCCESS === message_id=%s, chat_id=%s, open_id=%s, text=%s",
                        message_event.message_id, message_event.chat_id, 
                        message_event.open_id, message_event.text[:50] if message_event.text else "")

            payload = {
                "message_id": message_event.message_id,
                "chat_id": message_event.chat_id,
                "open_id": message_event.open_id,
                "text": message_event.text,
                "create_time": message_event.create_time,
            }

            # ========== 幂等检查 ==========
            is_duplicate, existing_task_id, new_task_id = idempotency_service.check_and_create(
                message_id=message_event.message_id,
                raw_payload=payload
            )

            # ========== 幂等命中日志 ==========
            if is_duplicate and existing_task_id:
                logger.info(
                    "Idempotency hit - message already processed: message_id=%s, existing_task_id=%s",
                    message_event.message_id,
                    existing_task_id
                )
                response_text = f"已接收任务，任务号：{existing_task_id}\n当前状态：duplicate (任务已存在)"
                feishu_client.send_text_reply(message_id=message_event.message_id, text=response_text)
                return

            if not new_task_id:
                logger.error("=== TASK_ID CREATE FAILED === message_id=%s", message_event.message_id)
                return

            # ========== 数据库写入成功日志 ==========
            logger.info(
                "=== DATABASE WRITE SUCCESS === message_id=%s, task_id=%s",
                message_event.message_id,
                new_task_id
            )

            # ========== Celery 入队 ==========
            logger.info("=== CELERY ENQUEUE START === task_id=%s", new_task_id)
            from app.tasks.ingress_tasks import process_ingress_message
            task = process_ingress_message.delay(
                new_task_id, 
                message_event.text, 
                message_event.open_id,
                message_event.message_id,
                message_event.chat_id
            )

            # ========== 更新任务状态为 queued ==========
            db = SessionLocal()
            try:
                task_record = db.query(TaskRecord).filter(TaskRecord.task_id == new_task_id).first()
                if task_record:
                    if _can_mark_task_queued(task_record.status):
                        task_record.status = TaskStatus.QUEUED.value
                        db.commit()
                    else:
                        logger.info(
                            "Skip setting queued for task_id=%s because current status is %s",
                            new_task_id,
                            task_record.status,
                        )
            finally:
                db.close()

            # ========== Celery 入队成功日志 ==========
            logger.info(
                "=== CELERY ENQUEUE SUCCESS === task_id=%s, celery_task_id=%s",
                new_task_id,
                task.id
            )

            # ========== 飞书回执 ==========
            logger.info("=== FEISHU REPLY START === message_id=%s, task_id=%s", message_event.message_id, new_task_id)
            is_confirm_cmd = bool(re.search(r"(?:确认执行|确认|执行)\s*TASK-[A-Z0-9][A-Z0-9-]{6,}", message_event.text, re.IGNORECASE))
            if is_confirm_cmd:
                response_text = f"已接收确认请求，任务号：{new_task_id}\n当前状态：执行中"
            else:
                response_text = f"已接收任务，任务号：{new_task_id}\n当前状态：queued"
            reply_success = feishu_client.send_text_reply(
                message_id=message_event.message_id, 
                text=response_text
            )

            # ========== 回执发送结果日志 ==========
            if reply_success:
                logger.info(
                    "=== FEISHU REPLY SUCCESS === message_id=%s, task_id=%s",
                    message_event.message_id,
                    new_task_id
                )
            else:
                logger.error(
                    "=== FEISHU REPLY FAILED === message_id=%s, task_id=%s",
                    message_event.message_id,
                    new_task_id
                )

            logger.info(
                "Message processed successfully: message_id=%s, task_id=%s, celery_task_id=%s",
                message_event.message_id,
                new_task_id,
                task.id
            )

        except Exception as e:
            logger.error("Error handling message event: %s", str(e), exc_info=True)

    @staticmethod
    def _safe_to_dict(value):
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if hasattr(value, "to_dict"):
            try:
                d = value.to_dict()
                if isinstance(d, dict):
                    return d
            except Exception:
                pass
        # Some Feishu SDK models expose fields via attributes only.
        raw_attrs = getattr(value, "__dict__", None)
        if isinstance(raw_attrs, dict):
            out: dict = {}
            for k, v in raw_attrs.items():
                if k.startswith("_"):
                    continue
                if isinstance(v, (str, int, float, bool)) or v is None:
                    out[k] = v
                    continue
                nested = FeishuLongConnListener._safe_to_dict(v)
                if nested is not None:
                    out[k] = nested
            if out:
                return out
        return None

    @staticmethod
    def _safe_json_loads(value):
        if not isinstance(value, str):
            return None
        text = value.strip()
        if not text:
            return None
        if not (text.startswith("{") and text.endswith("}")):
            return None
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
        return None

    @staticmethod
    def _coerce_value_to_dict(value):
        if isinstance(value, dict):
            return value
        dict_value = FeishuLongConnListener._safe_to_dict(value)
        if isinstance(dict_value, dict):
            return dict_value
        if isinstance(value, str):
            parsed = FeishuLongConnListener._safe_json_loads(value)
            if isinstance(parsed, dict):
                return parsed
        return {}

    @staticmethod
    def _walk_for_card_fields(node, result: dict, depth: int = 0, max_depth: int = 8):
        if node is None or depth > max_depth:
            return

        if isinstance(node, str):
            parsed = FeishuLongConnListener._safe_json_loads(node)
            if parsed:
                FeishuLongConnListener._walk_for_card_fields(parsed, result, depth + 1, max_depth)
            return

        if isinstance(node, dict):
            if "open_id" in node and not result.get("open_id"):
                result["open_id"] = str(node.get("open_id") or "")
            if "open_chat_id" in node and not result.get("chat_id"):
                result["chat_id"] = str(node.get("open_chat_id") or "")
            if "chat_id" in node and not result.get("chat_id"):
                result["chat_id"] = str(node.get("chat_id") or "")
            if "open_message_id" in node and not result.get("open_message_id"):
                result["open_message_id"] = str(node.get("open_message_id") or "")
            if "action" in node:
                action_candidate = FeishuLongConnListener._coerce_value_to_dict(node.get("action"))
                if action_candidate and not result.get("action_dict"):
                    result["action_dict"] = action_candidate
            if "value" in node and not result.get("value_dict"):
                value_candidate = FeishuLongConnListener._coerce_value_to_dict(node.get("value"))
                if value_candidate:
                    result["value_dict"] = value_candidate
            if "payload" in node and not result.get("raw_payload_text"):
                payload_text = node.get("payload")
                if isinstance(payload_text, str):
                    result["raw_payload_text"] = payload_text
            for v in node.values():
                FeishuLongConnListener._walk_for_card_fields(v, result, depth + 1, max_depth)
            return

        if isinstance(node, (list, tuple, set)):
            for item in node:
                FeishuLongConnListener._walk_for_card_fields(item, result, depth + 1, max_depth)
            return

        obj_dict = FeishuLongConnListener._safe_to_dict(node)
        if isinstance(obj_dict, dict):
            FeishuLongConnListener._walk_for_card_fields(obj_dict, result, depth + 1, max_depth)
            return

        attrs = ("payload", "raw_payload", "body", "raw", "event", "header", "action", "context", "operator", "value")
        for attr in attrs:
            try:
                attr_value = getattr(node, attr, None)
            except Exception:
                continue
            if attr_value is None:
                continue
            if attr in ("payload", "raw_payload", "body", "raw") and isinstance(attr_value, str) and not result.get("raw_payload_text"):
                result["raw_payload_text"] = attr_value
            FeishuLongConnListener._walk_for_card_fields(attr_value, result, depth + 1, max_depth)

    def _extract_card_action_envelope_layer1(self, data) -> dict:
        event_obj = getattr(data, "event", None)
        header_obj = getattr(data, "header", None)
        action_obj = getattr(event_obj, "action", None)
        context_obj = getattr(event_obj, "context", None)
        operator_obj = getattr(event_obj, "operator", None)
        value_obj = getattr(action_obj, "value", None)

        value_dict = self._coerce_value_to_dict(value_obj)
        action_dict = self._coerce_value_to_dict(action_obj)
        context_dict = self._coerce_value_to_dict(context_obj)
        operator_dict = self._coerce_value_to_dict(operator_obj)
        header_dict = self._coerce_value_to_dict(header_obj)
        event_dict = self._coerce_value_to_dict(event_obj)
        if action_dict:
            if value_dict:
                action_dict["value"] = value_dict
            event_dict["action"] = action_dict
        elif value_dict:
            event_dict["action"] = {"value": value_dict}
        if context_dict:
            event_dict["context"] = context_dict
        if operator_dict:
            event_dict["operator"] = operator_dict

        open_id = str(getattr(operator_obj, "open_id", "") or operator_dict.get("open_id") or "")
        chat_id = str(getattr(context_obj, "open_chat_id", "") or context_dict.get("open_chat_id") or event_dict.get("chat_id") or "")
        open_message_id = str(getattr(context_obj, "open_message_id", "") or context_dict.get("open_message_id") or event_dict.get("open_message_id") or "")

        if chat_id and "chat_id" not in event_dict:
            event_dict["chat_id"] = chat_id
        if open_message_id and "open_message_id" not in event_dict:
            event_dict["open_message_id"] = open_message_id
        if open_id and "open_id" not in event_dict:
            event_dict["open_id"] = open_id

        return {"header": header_dict, "event": event_dict}

    def _extract_card_action_envelope(self, data) -> dict:
        # Layer 1: direct SDK object attribute access.
        envelope = self._extract_card_action_envelope_layer1(data)
        event_dict = envelope.get("event") if isinstance(envelope.get("event"), dict) else {}
        action_dict = event_dict.get("action") if isinstance(event_dict.get("action"), dict) else {}
        value_dict = action_dict.get("value") if isinstance(action_dict.get("value"), dict) else {}
        if value_dict.get("action") and value_dict.get("batch_id") is not None and value_dict.get("candidate_index") is not None:
            logger.info(
                "=== P12 CARD ACTION RAW FALLBACK === data_type=%s, payload_text_len=%s, has_header=%s, has_event=%s",
                type(data),
                0,
                hasattr(data, "header"),
                hasattr(data, "event"),
            )
            logger.info("=== P12 CARD ACTION ENVELOPE BUILT === keys=%s event_keys=%s", list(envelope.keys()), list(event_dict.keys()))
            return envelope

        # Layer 2: recursively inspect SDK raw object structure.
        recursive_result = {}
        self._walk_for_card_fields(data, recursive_result)
        rec_open_id = str(recursive_result.get("open_id") or "")
        rec_chat_id = str(recursive_result.get("chat_id") or "")
        rec_open_message_id = str(recursive_result.get("open_message_id") or "")
        rec_action_dict = recursive_result.get("action_dict") if isinstance(recursive_result.get("action_dict"), dict) else {}
        rec_value_dict = recursive_result.get("value_dict") if isinstance(recursive_result.get("value_dict"), dict) else {}
        if rec_value_dict:
            if not rec_action_dict:
                rec_action_dict = {}
            rec_action_dict["value"] = rec_value_dict
        if rec_action_dict and "action" not in event_dict:
            event_dict["action"] = rec_action_dict
        elif rec_action_dict and isinstance(event_dict.get("action"), dict):
            event_dict["action"].update(rec_action_dict)
        if rec_open_id and not ((event_dict.get("operator") or {}).get("open_id") if isinstance(event_dict.get("operator"), dict) else ""):
            event_dict["operator"] = {"open_id": rec_open_id}
        if rec_chat_id and not event_dict.get("chat_id"):
            event_dict["chat_id"] = rec_chat_id
        if rec_open_message_id and not event_dict.get("open_message_id"):
            event_dict["open_message_id"] = rec_open_message_id
        envelope["event"] = event_dict
        action_dict = event_dict.get("action") if isinstance(event_dict.get("action"), dict) else {}
        value_dict = action_dict.get("value") if isinstance(action_dict.get("value"), dict) else {}
        if value_dict.get("action") and value_dict.get("batch_id") is not None and value_dict.get("candidate_index") is not None:
            logger.info(
                "=== P12 CARD ACTION RAW FALLBACK === data_type=%s, payload_text_len=%s, has_header=%s, has_event=%s",
                type(data),
                len(str(recursive_result.get("raw_payload_text") or "")),
                hasattr(data, "header"),
                hasattr(data, "event"),
            )
            logger.info("=== P12 CARD ACTION ENVELOPE BUILT === keys=%s event_keys=%s", list(envelope.keys()), list(event_dict.keys()))
            return envelope

        # Layer 3: fallback from raw payload JSON string.
        raw_payload_text = str(recursive_result.get("raw_payload_text") or "")
        logger.info(
            "=== P12 CARD ACTION RAW FALLBACK === data_type=%s, payload_text_len=%s, has_header=%s, has_event=%s",
            type(data),
            len(raw_payload_text),
            hasattr(data, "header"),
            hasattr(data, "event"),
        )
        raw_payload_dict = self._safe_json_loads(raw_payload_text) if raw_payload_text else None
        if isinstance(raw_payload_dict, dict):
            raw_event = raw_payload_dict.get("event") if isinstance(raw_payload_dict.get("event"), dict) else {}
            raw_header = raw_payload_dict.get("header") if isinstance(raw_payload_dict.get("header"), dict) else {}
            if raw_header and not envelope.get("header"):
                envelope["header"] = raw_header
            if raw_event:
                if not event_dict:
                    envelope["event"] = raw_event
                else:
                    for k, v in raw_event.items():
                        if k not in event_dict:
                            event_dict[k] = v
                    envelope["event"] = event_dict

        logger.info(
            "=== P12 CARD ACTION ENVELOPE BUILT === keys=%s event_keys=%s",
            list(envelope.keys()),
            list((envelope.get("event") if isinstance(envelope.get("event"), dict) else {}).keys()),
        )
        return envelope

    @staticmethod
    def _parse_card_action_payload(raw_dict: dict) -> dict:
        event = raw_dict.get("event") if isinstance(raw_dict.get("event"), dict) else {}
        action = event.get("action") if isinstance(event.get("action"), dict) else {}
        value = action.get("value") if isinstance(action.get("value"), dict) else {}
        action_name = str(value.get("action") or "").strip()
        if not action_name:
            raise ValueError("payload 缺少 action")
        return value

    @staticmethod
    def _parse_add_from_candidate_payload(value: dict) -> tuple[int, int, str]:
        try:
            batch_id = int(value.get("batch_id"))
            candidate_index = int(value.get("candidate_index"))
        except Exception as exc:
            raise ValueError("payload 缺少有效 batch_id 或 candidate_index") from exc
        query = str(value.get("query") or "").strip()
        return batch_id, candidate_index, query

    @staticmethod
    def _parse_manage_monitor_payload(value: dict) -> tuple[str, int]:
        action_name = str(value.get("action") or "").strip()
        try:
            target_id = int(value.get("target_id"))
        except Exception as exc:
            raise ValueError("payload 缺少有效 target_id") from exc
        if action_name not in {
            "pause_monitor_target",
            "resume_monitor_target",
            "delete_monitor_target_request",
            "delete_monitor_target_confirm",
            "delete_monitor_target_cancel",
        }:
            raise ValueError("不支持的管理动作")
        return action_name, target_id

    @staticmethod
    def _parse_monitor_targets_next_page_payload(value: dict) -> tuple[int, int]:
        action_name = str(value.get("action") or "").strip()
        if action_name != "monitor_targets_next_page":
            raise ValueError("不支持的分页动作")
        try:
            page = int(value.get("page"))
        except Exception as exc:
            raise ValueError("payload 缺少有效 page") from exc
        if page <= 0:
            raise ValueError("page 必须是大于 0 的整数")
        raw_limit = value.get("limit", 5)
        try:
            limit = int(raw_limit)
        except Exception:
            limit = 5
        if limit <= 0:
            limit = 5
        if limit > 20:
            limit = 20
        return page, limit

    @staticmethod
    def _resolve_card_reply_target(chat_id: str, open_id: str) -> tuple[str, str]:
        normalized_chat_id = str(chat_id or "").strip()
        normalized_open_id = str(open_id or "").strip()
        if normalized_chat_id:
            return "chat", normalized_chat_id
        return "open_id", normalized_open_id

    def _handle_card_action_event(self, data):
        action_name = ""
        try:
            raw_dict = self._extract_card_action_envelope(data)
            logger.info(
                "=== P12 CARD ACTION RECEIVED === raw_payload=%s",
                json.dumps(raw_dict, ensure_ascii=False)[:1000],
            )

            header = raw_dict.get("header") if isinstance(raw_dict.get("header"), dict) else {}
            event = raw_dict.get("event") if isinstance(raw_dict.get("event"), dict) else {}
            action = event.get("action") if isinstance(event.get("action"), dict) else {}

            open_id = (
                (header.get("user_id") if isinstance(header, dict) else None)
                or ((event.get("operator") or {}).get("open_id") if isinstance(event.get("operator"), dict) else None)
                or (event.get("open_id") if isinstance(event, dict) else None)
                or ((action.get("open_id")) if isinstance(action, dict) else None)
                or ""
            )
            open_message_id = str(event.get("open_message_id") or "")
            chat_id = str(event.get("chat_id") or ((event.get("context") or {}).get("open_chat_id") if isinstance(event.get("context"), dict) else "") or "")

            value = self._parse_card_action_payload(raw_dict)
            action_name = str(value.get("action") or "").strip()
            logger.info(
                "=== P12 CARD ACTION PAYLOAD === action=%s, value=%s, chat_id=%s, open_id=%s",
                action_name,
                value,
                chat_id,
                open_id,
            )
            if action_name not in {
                "add_from_candidate",
                "pause_monitor_target",
                "resume_monitor_target",
                "delete_monitor_target_request",
                "delete_monitor_target_confirm",
                "delete_monitor_target_cancel",
                "monitor_targets_next_page",
            }:
                logger.info("Ignore unsupported card action: %s", action_name)
                return

            if action_name == "add_from_candidate":
                batch_id, candidate_index, query = self._parse_add_from_candidate_payload(value)
                if candidate_index <= 0:
                    raise ValueError("候选编号必须是大于 0 的整数")
                if not open_id:
                    raise ValueError("无法识别操作人，缺少 open_id")

                context = _load_latest_discovery_context(chat_id=chat_id, user_open_id=open_id)
                if not context:
                    raise ValueError("候选结果已失效，请先发送“搜索商品：关键词”")
                context_batch_id = context.get("batch_id")
                if context_batch_id in (None, "") or int(context_batch_id) != batch_id:
                    raise ValueError("候选结果批次不匹配，请重新搜索商品后再试")

                action_state = {
                    "intent_code": "ecom_watch.add_from_candidates",
                    "slots": {"index": candidate_index},
                    "status": "processing",
                    "source_chat_id": chat_id,
                    "user_open_id": open_id,
                }
                logger.info(
                    "=== P12 CARD ACTION ADD START === batch_id=%s, candidate_index=%s, query=%s, chat_id=%s, open_id=%s",
                    batch_id,
                    candidate_index,
                    query,
                    chat_id,
                    open_id,
                )
                result = execute_action(action_state)
                result_text = str(result.get("result_summary") or "").strip() or "未能加入监控，请稍后重试。"
                logger.info(
                    "=== P12 CARD ACTION ADD SUCCESS === action=%s batch_id=%s index=%s open_message_id=%s query=%s status=%s",
                    action_name,
                    batch_id,
                    candidate_index,
                    open_message_id,
                    query,
                    result.get("status"),
                )
            elif action_name in {
                "pause_monitor_target",
                "resume_monitor_target",
                "delete_monitor_target_request",
                "delete_monitor_target_confirm",
                "delete_monitor_target_cancel",
            }:
                action_name, target_id = self._parse_manage_monitor_payload(value)
                b_client = BServiceClient()
                if action_name == "pause_monitor_target":
                    b_client.pause_monitor_target(target_id)
                    result_text = f"已暂停监控。\n- 对象ID：{target_id}\n- 状态：inactive"
                elif action_name == "resume_monitor_target":
                    b_client.resume_monitor_target(target_id)
                    result_text = f"已恢复监控。\n- 对象ID：{target_id}\n- 状态：active"
                elif action_name == "delete_monitor_target_request":
                    targets_data = b_client.get_monitor_targets()
                    targets = self._extract_monitor_targets_list(targets_data)
                    selected = None
                    for item in targets:
                        raw_id = item.get("target_id")
                        if raw_id in (None, ""):
                            raw_id = item.get("id") or item.get("product_id")
                        try:
                            if int(raw_id) == target_id:
                                selected = item
                                break
                        except Exception:
                            continue
                    if selected is None:
                        raise ValueError(f"未找到对象ID={target_id} 的监控对象")

                    card = build_monitor_target_delete_confirm_card(target=selected)
                    send_ok = False
                    if chat_id:
                        send_ok = feishu_client.send_interactive_message(
                            receive_id=chat_id,
                            card=card,
                            receive_id_type="chat_id",
                        )
                    elif open_id:
                        send_ok = feishu_client.send_interactive_message(
                            receive_id=open_id,
                            card=card,
                            receive_id_type="open_id",
                        )
                    if send_ok:
                        logger.info(
                            "=== P12-F DELETE REQUEST CARD SENT === target_id=%s open_message_id=%s",
                            target_id,
                            open_message_id,
                        )
                        return
                    result_text = (
                        "删除确认卡片发送失败，请稍后重试。\n"
                        f"- 对象ID：{target_id}"
                    )
                elif action_name == "delete_monitor_target_confirm":
                    logger.info("=== P12 DELETE CONFIRM START === target_id=%s", target_id)
                    delete_raw_response = b_client.delete_monitor_target_raw_response(target_id)
                    logger.info(
                        "=== P12 DELETE B RESPONSE === target_id=%s response=%s",
                        target_id,
                        json.dumps(delete_raw_response, ensure_ascii=False),
                    )
                    logger.info("=== P12 DELETE VERIFY START === target_id=%s", target_id)
                    targets_data = b_client.get_monitor_targets()
                    targets = self._extract_monitor_targets_list(targets_data)
                    exists, status = self._find_target_in_list(targets, target_id)
                    logger.info(
                        "=== P12 DELETE VERIFY RESULT === exists=%s status=%s target_id=%s",
                        str(exists).lower(),
                        status,
                        target_id,
                    )
                    if exists:
                        result_text = (
                            "删除未确认，请稍后重试或检查服务状态。\n"
                            f"- 对象ID：{target_id}\n"
                            f"- 当前状态：{status}"
                        )
                    else:
                        result_text = f"已删除监控对象。\n- 对象ID：{target_id}"
                else:
                    result_text = f"已取消删除。\n- 对象ID：{target_id}\n对象仍保留在监控列表。"
                logger.info(
                    "=== P12-CF MONITOR MANAGE SUCCESS === action=%s target_id=%s open_message_id=%s",
                    action_name,
                    target_id,
                    open_message_id,
                )
            else:
                page, limit = self._parse_monitor_targets_next_page_payload(value)
                b_client = BServiceClient()
                targets_data = b_client.get_monitor_targets()
                targets = self._extract_monitor_targets_list(targets_data)
                total = len(targets)
                start = (page - 1) * limit
                if start >= total:
                    result_text = f"没有更多监控对象了。\n- 总数：{total}\n- 当前页：{page}"
                    logger.info(
                        "=== P12-D MONITOR NEXT PAGE EMPTY === page=%s limit=%s total=%s open_message_id=%s",
                        page,
                        limit,
                        total,
                        open_message_id,
                    )
                else:
                    card = build_monitor_targets_card(
                        targets=targets,
                        page=page,
                        limit=limit,
                    )
                    send_ok = False
                    if chat_id:
                        send_ok = feishu_client.send_interactive_message(
                            receive_id=chat_id,
                            card=card,
                            receive_id_type="chat_id",
                        )
                    elif open_id:
                        send_ok = feishu_client.send_interactive_message(
                            receive_id=open_id,
                            card=card,
                            receive_id_type="open_id",
                        )
                    if send_ok:
                        logger.info(
                            "=== P12-D MONITOR NEXT PAGE CARD SENT === page=%s limit=%s total=%s open_message_id=%s",
                            page,
                            limit,
                            total,
                            open_message_id,
                        )
                        return
                    result_text = (
                        f"监控对象第 {page} 页（每页 {limit} 条）\n"
                        f"卡片发送失败，请稍后重试。"
                    )
                    logger.warning(
                        "=== P12-D MONITOR NEXT PAGE CARD FAILED === page=%s limit=%s total=%s open_message_id=%s",
                        page,
                        limit,
                        total,
                        open_message_id,
                    )

            reply_target_type, reply_target_id = self._resolve_card_reply_target(chat_id=chat_id, open_id=open_id)
            logger.info(
                "=== P12 CARD ACTION REPLY TARGET === target_type=%s target_id=%s",
                reply_target_type,
                reply_target_id,
            )
            if reply_target_type == "chat":
                feishu_client.send_text_message(receive_id=reply_target_id, text=result_text, receive_id_type="chat_id")
            else:
                feishu_client.send_text_message(receive_id=reply_target_id, text=result_text, receive_id_type="open_id")
        except Exception as e:
            if action_name in {
                "pause_monitor_target",
                "resume_monitor_target",
                "delete_monitor_target_request",
                "delete_monitor_target_confirm",
                "delete_monitor_target_cancel",
            }:
                error_text = f"未能完成监控操作。\n原因：{str(e)}"
            elif action_name == "monitor_targets_next_page":
                error_text = f"未能加载更多监控对象。\n原因：{str(e)}"
            else:
                error_text = f"未能加入监控。\n原因：{str(e)}\n可继续使用“加入监控第 N 个”重试。"
            try:
                raw_dict = self._extract_card_action_envelope(data)
                event = raw_dict.get("event") if isinstance(raw_dict.get("event"), dict) else {}
                chat_id = str(event.get("chat_id") or ((event.get("context") or {}).get("open_chat_id") if isinstance(event.get("context"), dict) else "") or "")
                open_id = (
                    ((event.get("operator") or {}).get("open_id") if isinstance(event.get("operator"), dict) else "")
                    or str(event.get("open_id") or "")
                )
                reply_target_type, reply_target_id = self._resolve_card_reply_target(chat_id=chat_id, open_id=open_id)
                logger.info(
                    "=== P12 CARD ACTION REPLY TARGET === target_type=%s target_id=%s",
                    reply_target_type,
                    reply_target_id,
                )
                if reply_target_id:
                    if reply_target_type == "chat":
                        feishu_client.send_text_message(receive_id=reply_target_id, text=error_text, receive_id_type="chat_id")
                    else:
                        feishu_client.send_text_message(receive_id=reply_target_id, text=error_text, receive_id_type="open_id")
            except Exception:
                pass
            logger.error("=== P12 CARD ACTION ADD FAILED === reason=%s", str(e), exc_info=True)

    def start(self):
        if self._running:
            logger.warning("Long connection listener already running")
            return
        if lark is None or EventDispatcherHandler is None or LogLevel is None:
            raise RuntimeError("lark_oapi SDK 不可用，无法启动飞书长连接监听")

        logger.info("Starting Feishu long connection listener... app_id=%s", settings.FEISHU_APP_ID[:10]+"...")

        event_handler = (
            EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(self._handle_message_event)
            .register_p2_card_action_trigger(self._handle_card_action_event)
            .build()
        )

        self._client = lark.ws.Client(
            app_id=settings.FEISHU_APP_ID,
            app_secret=settings.FEISHU_APP_SECRET,
            event_handler=event_handler,
            log_level=LogLevel.DEBUG,
        )

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
        # 等待一下确认连接成功
        time.sleep(2)
        logger.info("Feishu long connection listener started, thread running")

    def _run(self):
        try:
            logger.info("WebSocket client starting...")
            self._client.start()
        except Exception as e:
            logger.error("Long connection error: %s", str(e), exc_info=True)
            self._running = False

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._client:
            logger.info("Stopping Feishu long connection listener")


longconn_listener = FeishuLongConnListener()