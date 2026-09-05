#!/usr/bin/env python3
"""
AI日报自动发送脚本 - 支持成本统计
用法: python3 send_report.py "日报内容" [输入Token数] [输出Token数]
"""

import requests
import json
import sys
from datetime import datetime

# 飞书配置


# MiniMax M2.5 价格
INPUT_PRICE_PER_MILLION = 1.95  # 元/百万Token
OUTPUT_PRICE_PER_MILLION = 17.3  # 元/百万Token

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": APP_ID, "app_secret": APP_SECRET}
    resp = requests.post(url, json=data).json()
    return resp.get("tenant_access_token")

def calculate_cost(input_tokens=0, output_tokens=0):
    """计算API调用成本"""
    input_cost = (input_tokens / 1_000_000) * INPUT_PRICE_PER_MILLION
    output_cost = (output_tokens / 1_000_000) * OUTPUT_PRICE_PER_MILLION
    total = input_cost + output_cost
    return round(total, 4)

def format_report(content, input_tokens=0, output_tokens=0):
    """格式化日报内容，包含成本统计"""
    cost = calculate_cost(input_tokens, output_tokens)
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 如果没有传入Token，显示待统计
    if input_tokens == 0 and output_tokens == 0:
        cost_section = f"""## 今日预估成本
| 项目 | 数值 | 单价 | 费用(元) |
|------|------|------|----------|
| 输入Token | 待统计 | ¥1.95/百万 | - |
| 输出Token | 待统计 | ¥17.3/百万 | - |
| **总计** | - | - | 待统计 |

> 模型: MiniMax M2.5"""
    else:
        cost_section = f"""## 今日预估成本
| 项目 | 数值 | 单价 | 费用(元) |
|------|------|------|----------|
| 输入Token | {input_tokens:,} | ¥1.95/百万 | {input_tokens/1_000_000*INPUT_PRICE_PER_MILLION:.4f} |
| 输出Token | {output_tokens:,} | ¥17.3/百万 | {output_tokens/1_000_000*OUTPUT_PRICE_PER_MILLION:.4f} |
| **总计** | - | - | **¥{cost}** |

> 模型: MiniMax M2.5"""
    
    full_report = f"""# AI工作日报 - {today}

{content}

{cost_section}

---
汇报时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""
    return full_report

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
    # 获取参数
    content = sys.argv[1] if len(sys.argv) > 1 else "任务完成"
    input_tokens = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    output_tokens = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    
    # 格式化报告
    full_report = format_report(content, input_tokens, output_tokens)
    
    # 获取token并发送
    token = get_token()
    result = send_message(token, full_report)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 如果有成本，显示费用
    if input_tokens > 0 or output_tokens > 0:
        cost = calculate_cost(input_tokens, output_tokens)
        print(f"\n今日预估成本: ¥{cost}")
