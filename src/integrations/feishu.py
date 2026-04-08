import requests
import json
from src.config import config


class FeishuClient:
    """Feishu API client"""
    
    def __init__(self):
        self.app_id = config.FEISHU_APP_ID
        self.app_secret = config.FEISHU_APP_SECRET
        self.token = None
    
    def get_token(self):
        """Get access token"""
        url = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal/"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        response = requests.post(url, json=payload)
        data = response.json()
        if data.get("code") == 0:
            self.token = data.get("app_access_token")
            return self.token
        raise Exception(f"Failed to get token: {data}")
    
    def send_message(self, user_id, content):
        """Send message to user"""
        if not self.token:
            self.get_token()
        
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "receive_id_type": "user_id",
            "receive_id": user_id,
            "content": json.dumps({"text": content}),
            "msg_type": "text"
        }
        response = requests.post(url, headers=headers, json=payload)
        return response.json()
    
    def send_card(self, user_id, card):
        """Send interactive card to user"""
        if not self.token:
            self.get_token()
        
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        payload = {
            "receive_id_type": "user_id",
            "receive_id": user_id,
            "content": json.dumps(card),
            "msg_type": "interactive"
        }
        response = requests.post(url, headers=headers, json=payload)
        return response.json()