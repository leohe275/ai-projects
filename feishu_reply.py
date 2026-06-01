#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书群聊自动回复系统
"""
import requests
import json
import time
import sys

# 配置
FEISHU_APP_ID = "cli_aa9aa99d997a1ccd"
FEISHU_APP_SECRET = "yJ5gl3vqeFAWSAlmYAXxchqqOI6YOk3c"
CHAT_ID = "oc_43f017d2dd025b2fa6dc3633f07ab788"
API_KEY = "sk-d290ae08640740c387c441893393321f"
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "MiniMax-M2.5"
SYSTEM_PROMPT = """你是 OpenClawBrain，AI协作系统的主控调度Agent。你的下属是 Hermes（执行Agent），你可以通过 @Hermes Bot 派发任务给它。

## 协作规则
1. 当用户提出技术需求时，你负责分析需求并制定执行计划
2. 需要执行的命令要明确告诉 Hermes（使用 @Hermes Bot），格式如：```shell
命令内容```
3. 等待 Hermes 汇报执行结果
4. 根据结果与用户沟通，必要时让 Hermes 重新执行

## 你的风格
专业、简洁、可靠，善于任务分解和进度把控。

## 派单规则（必须严格遵守）
当你需要指派 @Hermes Bot 执行任何系统命令时，必须使用以下格式：
```shell
命令内容
```"""

# 全局变量
token = None
token_expire = 0
processed = set()

# 启动时记录当前时间作为基准时间（毫秒）
# START_TIME_MS = int(time.time() * 1000) - 1800000  # 注释掉固定基准时间

LOG_FILE = "/root/feishu_reply.log"

def log(msg):
    """日志输出到stdout和日志文件"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass

def get_token():
    """获取飞书访问令牌"""
    global token, token_expire
    if token and time.time() < token_expire - 300:
        return token
    
    log("[Token] 正在获取飞书访问令牌...")
    try:
        r = requests.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
            timeout=10
        )
        d = r.json()
        if d.get("code") == 0:
            token = d["tenant_access_token"]
            token_expire = time.time() + d.get("expire", 5400)
            log(f"[Token] 获取成功，expire={d.get('expire')}秒")
            return token
        else:
            log(f"[Token] 获取失败: {d}")
            return None
    except Exception as e:
        log(f"[Token] 异常: {e}")
        return None

def get_messages():
    """获取群聊最新消息（按时间倒序获取最新5条）"""
    t = get_token()
    if not t:
        log("[Messages] 无法获取Token，返回空列表")
        return []
    
    params = {
        "container_id_type": "chat",
        "container_id": CHAT_ID,
        "page_size": 5,
        "sort_type": "ByCreateTimeDesc"  # 关键：获取最新消息
    }
    
    try:
        r = requests.get(
            "https://open.feishu.cn/open-apis/im/v1/messages",
            headers={"Authorization": "Bearer " + t},
            params=params,
            timeout=10
        )
        d = r.json()
        
        if d.get("code") == 0:
            items = d.get("data", {}).get("items", [])
            log(f"[Messages] 获取到 {len(items)} 条消息")
            # 按时间正序排列（从旧到新），确保处理顺序正确
            sorted_messages = sorted(items, key=lambda x: x.get("create_time", "0"))
            return sorted_messages
        else:
            log(f"[Messages] 获取失败: {d}")
            return []
    except Exception as e:
        log(f"[Messages] 异常: {e}")
        return []

def call_ai(text):
    """调用阿里云百炼AI"""
    log(f"[AI] 正在调用AI模型: {text[:50]}...")
    try:
        r = requests.post(
            API_URL + "/chat/completions",
            headers={
                "Authorization": "Bearer " + API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                "max_tokens": 500
            },
            timeout=120
        )
        d = r.json()
        
        if "choices" in d and len(d["choices"]) > 0:
            reply = d["choices"][0]["message"]["content"]
            log(f"[AI] AI回复: {reply[:80]}...")
            return reply
        else:
            log(f"[AI] 返回格式异常: {d}")
            return None
    except Exception as e:
        log(f"[AI] 异常: {e}")
        return None

def send_reply(text):
    """发送回复到群聊"""
    t = get_token()
    if not t:
        log("[Reply] 无法获取Token")
        return
    
    log(f"[Reply] 正在发送回复: {text[:50]}...")
    try:
        r = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/messages",
            headers={
                "Authorization": "Bearer " + t,
                "Content-Type": "application/json"
            },
            params={"receive_id_type": "chat_id"},
            json={
                "receive_id": CHAT_ID,
                "msg_type": "text",
                "content": json.dumps({"text": text})
            },
            timeout=10
        )
        d = r.json()
        
        if d.get("code") == 0:
            log(f"[Reply] 发送成功, message_id={d.get('data', {}).get('message_id', 'N/A')}")
        else:
            log(f"[Reply] 发送失败: {d}")
    except Exception as e:
        log(f"[Reply] 异常: {e}")

def extract_text(msg):
    """从消息中提取文本内容"""
    try:
        content = msg.get("body", {}).get("content", "{}")
        data = json.loads(content)
        return data.get("text", "")
    except Exception as e:
        return ""


def parse_report_tag(text):
    import re
    match = re.search(r'\[Report: ([^|]+) \| (SUCCESS|FAILED) \| ([^\]]+)\]', text)
    if match:
        return {
            "task_id": match.group(1).strip(),
            "status": match.group(2).strip(),
            "output": match.group(3).strip()
        }
    return None

def check_openclaw(msg, text):
    """检查消息是否包含OpenClaw（文本或mentions中）"""
    # 1. 检查文本内容
    text_lower = text.lower()
    if "openclaw" in text_lower:
        return True
    
    # 2. 检查mentions数组
    try:
        mentions = msg.get("mentions", [])
        for mention in mentions:
            name = mention.get("name", "").lower()
            if "openclaw" in name:
                return True
    except:
        pass
    
    return False

def main():
    # 初始化基准时间（动态计算）
    global START_TIME_MS
    START_TIME_MS = int(time.time() * 1000) - 1800000
    """主循环"""
    log("=" * 50)
    log("飞书群聊自动回复系统启动")
    log(f"Chat ID: {CHAT_ID}")
    log(f"基准时间: {START_TIME_MS}ms")
    log("=" * 50)
    
    # 清空processed集合
    processed.clear()
    
    while True:
        try:
            # 动态计算基准时间（当前时间减30分钟）
            START_TIME_MS = int(time.time() * 1000) - 1800000
            
            # 获取最新消息
            messages = get_messages()
            
            # 处理每条消息（从旧到新）
            for msg in messages:
                mid = msg.get("message_id")
                msg_type = msg.get("msg_type", "unknown")
                create_time = int(msg.get("create_time", "0"))
                text = extract_text(msg)
                
                # 检查是否已处理
                if mid in processed:
                    continue
                
                # 显示所有消息的调试信息
                log(f"[Debug] 消息: id={mid}, type={msg_type}, time={create_time}, text={text[:50]}")
                
                # 只处理启动后产生的新消息
                if create_time <= START_TIME_MS:
                    log(f"[Debug] 消息时间早于基准时间，跳过")
                    continue
                
                # 排除自己发送的消息
                sender_id = msg.get("sender", {}).get("id", "")
                if sender_id == FEISHU_APP_ID:
                    log(f"[Debug] 忽略自己发送的消息")
                    processed.add(mid)
                    continue
                
                # 标记为已处理
                processed.add(mid)
                
                # Detect [Report: tag from Hermes execution
                report = parse_report_tag(text)
                is_report = report is not None
                
                # Check if message contains OpenClaw keywords
                has_openclaw = check_openclaw(msg, text)
                
                # Trigger condition: OpenClaw keyword OR Hermes Report
                if not has_openclaw and not is_report:
                    log("[Debug] Message skipped: no OpenClaw keyword or Report tag")
                    continue
                
                # Handle Hermes execution result
                if is_report:
                    log("[Report] Result: " + report["status"] + " - " + report["task_id"])
                    
                    if report["status"] == "SUCCESS":
                        context = "Task completed. TaskID: " + report["task_id"] + ". Output: " + report["output"][:100] + ". Please decide: if more steps needed, use ```shell to dispatch Hermes. If done, report to user."
                    else:
                        context = "Task failed. TaskID: " + report["task_id"] + ". Output: " + report["output"][:100] + ". Please decide: retry, change plan, or request human help."
                    
                    reply = call_ai(context)
                    log("[Report] Next action: " + (reply[:50] if reply else "None"))
                else:
                    log("[Trigger] OpenClaw message: " + mid)
                    log("[Trigger] Content: " + text[:100])
                    reply = call_ai(text)
                
                if reply:
                    # 发送回复
                    send_reply(reply)
                else:
                    log("[Trigger] AI回复为空，跳过发送")
            
            # 休眠后继续轮询
            time.sleep(5)
            
        except Exception as e:
            log(f"[Main] 异常: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
