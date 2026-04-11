from fastapi import APIRouter, Request, Response
from app.schemas.common import CommonResponse

router = APIRouter(prefix="/feishu", tags=["feishu"])


@router.post("/event")
async def feishu_webhook_event(request: Request):
    """
    TODO: 预留飞书 Webhook HTTP 回调入口
    当前版本使用长连接模式，此接口暂不启用
    
    后续正式环境需要：
    1. 配置公网回调地址
    2. 实现 challenge 校验
    3. 实现签名验签
    """
    return CommonResponse(code=0, message="webhook placeholder")


@router.get("/event")
async def feishu_webhook_challenge(request: Request):
    """
    TODO: 预留飞书 Webhook challenge 验证
    用于飞书服务器验证回调地址有效性
    """
    return CommonResponse(code=0, message="challenge placeholder")