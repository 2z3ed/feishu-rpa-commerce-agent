from __future__ import annotations

try:
    import lark_oapi as lark  # type: ignore
except Exception:  # pragma: no cover
    lark = None  # type: ignore[assignment]

from app.core.config import settings
from app.core.logging import logger


class FeishuFileDownloadError(RuntimeError):
    def __init__(self, *, reason: str, attachment_type: str, message_id: str, resource_type: str, endpoint_kind: str, http_status: int | None = None, feishu_code: str | None = None, feishu_msg: str | None = None, error_class: str | None = None, error_message_safe: str | None = None, retryable: bool | None = None):
        super().__init__(error_message_safe or reason)
        self.reason = reason
        self.attachment_type = attachment_type
        self.message_id = message_id
        self.resource_type = resource_type
        self.endpoint_kind = endpoint_kind
        self.http_status = http_status
        self.feishu_code = feishu_code
        self.feishu_msg = feishu_msg
        self.error_class = error_class or self.__class__.__name__
        self.error_message_safe = error_message_safe or reason
        self.retryable = retryable


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
            self._client = lark.Client().builder()\
                .app_id(settings.FEISHU_APP_ID)\
                .app_secret(settings.FEISHU_APP_SECRET)\
                .log_level(lark.LogLevel.INFO)\
                .build()
        return self._client

    def send_text_message(self, receive_id: str, text: str, receive_id_type: str = "open_id") -> bool:
        try:
            if lark is None:
                raise RuntimeError("lark_oapi is not installed")
            from lark_oapi.api.im.v1.model import CreateMessageRequest, CreateMessageRequestBody

            request = (
                CreateMessageRequest.builder()
                .receive_id_type(receive_id_type)
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
                logger.info(
                    "Feishu message sent successfully: receive_id_type=%s, receive_id=%s",
                    receive_id_type,
                    receive_id,
                )
                return True
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
            logger.error("=== FEISHU REPLY FAILED ===: code=%s, msg=%s", response.code, response.msg)
            return False
        except Exception as e:
            logger.error("=== FEISHU REPLY FAILED ===: %s", str(e))
            return False

    def send_interactive_reply(self, message_id: str, card: dict) -> bool:
        try:
            logger.info(
                "=== FEISHU INTERACTIVE REPLY START === message_id=%s, card_keys=%s",
                message_id,
                list(card.keys()) if isinstance(card, dict) else [],
            )
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
                "=== FEISHU INTERACTIVE REPLY FAILED ===: message_id=%s, code=%s, msg=%s",
                message_id,
                response.code,
                response.msg,
            )
            return False
        except Exception as e:
            logger.error("=== FEISHU INTERACTIVE REPLY FAILED ===: %s", str(e), exc_info=True)
            return False

    def send_interactive_message(self, receive_id: str, card: dict, receive_id_type: str = "open_id") -> bool:
        try:
            logger.info(
                "=== FEISHU INTERACTIVE MESSAGE START === receive_id_type=%s, receive_id=%s",
                receive_id_type,
                receive_id,
            )
            if lark is None:
                raise RuntimeError("lark_oapi is not installed")
            from lark_oapi.api.im.v1.model import CreateMessageRequest, CreateMessageRequestBody

            request = (
                CreateMessageRequest.builder()
                .receive_id_type(receive_id_type)
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(receive_id)
                    .msg_type("interactive")
                    .content(lark.JSON.marshal(card))
                    .build()
                )
                .build()
            )
            response = self.client.im.v1.message.create(request)
            if response.code == 0:
                logger.info(
                    "=== FEISHU INTERACTIVE MESSAGE SUCCESS === receive_id_type=%s, receive_id=%s",
                    receive_id_type,
                    receive_id,
                )
                return True
            logger.error(
                "=== FEISHU INTERACTIVE MESSAGE FAILED ===: receive_id_type=%s, receive_id=%s, code=%s, msg=%s",
                receive_id_type,
                receive_id,
                response.code,
                response.msg,
            )
            return False
        except Exception as e:
            logger.error("=== FEISHU INTERACTIVE MESSAGE FAILED ===: %s", str(e), exc_info=True)
            return False

    def download_message_resource(self, message_id: str, file_key: str, attachment_type: str) -> bytes:
        try:
            if lark is None:
                raise RuntimeError("lark_oapi is not installed")
            from lark_oapi.api.im.v1.model import GetMessageResourceRequest

            resource_type = "image" if attachment_type == "image" else "file"
            req = (
                GetMessageResourceRequest.builder()
                .message_id(message_id)
                .file_key(file_key)
                .type(resource_type)
                .build()
            )
            resp = self.client.im.v1.message_resource.get(req)
            if resp.code != 0:
                raise FeishuFileDownloadError(
                    reason="feishu_api_error",
                    attachment_type=attachment_type,
                    message_id=message_id,
                    resource_type=resource_type,
                    endpoint_kind="im.v1.message_resource.get",
                    http_status=None,
                    feishu_code=str(getattr(resp, "code", None) or ""),
                    feishu_msg=str(getattr(resp, "msg", None) or ""),
                    error_message_safe="feishu_download_failed",
                    retryable=False,
                )
            if not hasattr(resp, "file") or resp.file is None:
                raise FeishuFileDownloadError(
                    reason="feishu_download_empty",
                    attachment_type=attachment_type,
                    message_id=message_id,
                    resource_type=resource_type,
                    endpoint_kind="im.v1.message_resource.get",
                    http_status=None,
                    feishu_code=str(getattr(resp, "code", None) or ""),
                    feishu_msg=str(getattr(resp, "msg", None) or ""),
                    error_message_safe="feishu_download_empty",
                    retryable=False,
                )
            return resp.file.read()
        except FeishuFileDownloadError:
            raise
        except Exception as exc:
            logger.error("Feishu file download exception: %s", str(exc))
            raise FeishuFileDownloadError(
                reason="exception",
                attachment_type=attachment_type,
                message_id=message_id,
                resource_type="image" if attachment_type == "image" else "file",
                endpoint_kind="im.v1.message_resource.get",
                error_class=exc.__class__.__name__,
                error_message_safe=str(exc)[:200],
                retryable=True,
            ) from exc


feishu_client = FeishuClient()
