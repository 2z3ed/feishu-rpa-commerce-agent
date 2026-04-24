from __future__ import annotations

try:
    import lark_oapi as lark  # type: ignore
except Exception:  # pragma: no cover
    lark = None  # type: ignore[assignment]

from app.core.config import settings
from app.core.logging import logger


class FeishuClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
        return cls._instance

    @property
    def client(self):
        if lark is None:
            raise RuntimeError("lark_oapi is not installed")
        if self._client is None:
            # 使用 builder 模式初始化客户端
            self._client = lark.Client().builder()\
                .app_id(settings.FEISHU_APP_ID)\
                .app_secret(settings.FEISHU_APP_SECRET)\
                .log_level(lark.LogLevel.DEBUG)\
                .build()
        return self._client

    def send_text_message(self, receive_id: str, text: str) -> bool:
        try:
            if lark is None:
                raise RuntimeError("lark_oapi is not installed")
            from lark_oapi.api.im.v1.model import CreateMessageRequest, CreateMessageRequestBody
            
            request = (
                CreateMessageRequest.builder()
                .receive_id_type("open_id")
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(receive_id)
                    .msg_type("text")
                    .content(lark.JSON.marshal({"text": text}))
                    .build()
                )
                .build()
            )
            response = self.client.im.v1.message.create(request)
            if response.code == 0:
                logger.info("Feishu message sent successfully: receive_id=%s", receive_id)
                return True
            else:
                logger.error("Feishu message send failed: code=%s, msg=%s", response.code, response.msg)
                return False
        except Exception as e:
            logger.error("Feishu message send exception: %s", str(e))
            return False

    def send_text_reply(self, message_id: str, text: str) -> bool:
        try:
            logger.info("=== FEISHU REPLY START ===")
            if lark is None:
                raise RuntimeError("lark_oapi is not installed")
            from lark_oapi.api.im.v1.model import ReplyMessageRequest, ReplyMessageRequestBody
            
            request = (
                ReplyMessageRequest.builder()
                .message_id(message_id)
                .request_body(
                    ReplyMessageRequestBody.builder()
                    .msg_type("text")
                    .content(lark.JSON.marshal({"text": text}))
                    .build()
                )
                .build()
            )
            response = self.client.im.v1.message.reply(request)
            if response.code == 0:
                logger.info("=== FEISHU REPLY SUCCESS ===: message_id=%s", message_id)
                return True
            else:
                logger.error("=== FEISHU REPLY FAILED ===: code=%s, msg=%s", response.code, response.msg)
                return False
        except Exception as e:
            logger.error("=== FEISHU REPLY FAILED ===: %s", str(e))
            return False

    def send_interactive_reply(self, message_id: str, card: dict) -> bool:
        try:
            logger.info("=== FEISHU INTERACTIVE REPLY START ===")
            if lark is None:
                raise RuntimeError("lark_oapi is not installed")
            from lark_oapi.api.im.v1.model import ReplyMessageRequest, ReplyMessageRequestBody

            request = (
                ReplyMessageRequest.builder()
                .message_id(message_id)
                .request_body(
                    ReplyMessageRequestBody.builder()
                    .msg_type("interactive")
                    .content(lark.JSON.marshal(card))
                    .build()
                )
                .build()
            )
            response = self.client.im.v1.message.reply(request)
            if response.code == 0:
                logger.info("=== FEISHU INTERACTIVE REPLY SUCCESS ===: message_id=%s", message_id)
                return True
            logger.error(
                "=== FEISHU INTERACTIVE REPLY FAILED ===: code=%s, msg=%s",
                response.code,
                response.msg,
            )
            return False
        except Exception as e:
            logger.error("=== FEISHU INTERACTIVE REPLY FAILED ===: %s", str(e))
            return False


feishu_client = FeishuClient()