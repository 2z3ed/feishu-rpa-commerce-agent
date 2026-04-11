from enum import Enum


class TaskStatus(str, Enum):
    RECEIVED = "received"
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    AWAITING_CONFIRMATION = "awaiting_confirmation"


class SourcePlatform(str, Enum):
    FEISHU = "feishu"
    WOOCOMMERCE = "woocommerce"
    ODOO = "odoo"
    CHATWOOT = "chatwoot"


class EventType(str, Enum):
    IM_MESSAGE_RECEIVE_V1 = "im.message.receive_v1"


FEISHU_EVENT_TYPES = [
    "im.message.receive_v1",
]


TASK_ID_PREFIX = "TASK-"
TASK_ID_DATE_FMT = "%Y%m%d"