#!/usr/bin/env python3
"""
AI日报自动发送脚本
用法: python3 send_report.py "日报内容"
"""

import requests
import json
import sys
from datetime import datetime

# 飞书配置
APP_ID = "cli_aa8ec1c206f89cc7"
APP_SECRET = "xsOml10gX1W3Lcn4E0r6tl6qCqKtJysi"
CHAT_ID = "oc_43f017d2dd025b2fa6dc3633f07ab788"

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": APP_ID, "app_secret": APP_SECRET}
    resp = requests.post(url, json=data).json()
    return resp.get("tenant_access_token")

def send_message(token, content):
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "receive_id": CHAT_ID,
        "msg_type": "text",
        "content": json.dumps({"text": content})
    }
    resp = requests.post(url, headers=headers, json=data).json()
    return resp

if __name__ == "__main__":
    content = sys.argv[1] if len(sys.argv) > 1 else "测试日报"
    token = get_token()
    result = send_message(token, content)
    print(json.dumps(result, ensure_ascii=False))
