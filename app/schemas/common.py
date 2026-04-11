from pydantic import BaseModel


class CommonResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: dict | None = None