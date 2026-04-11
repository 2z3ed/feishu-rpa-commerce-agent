from pydantic import BaseModel, Field


class FeishuMessagePayload(BaseModel):
    message_id: str
    chat_id: str
    open_id: str
    text: str
    create_time: str


class HealthResponse(BaseModel):
    status: str
    message: str