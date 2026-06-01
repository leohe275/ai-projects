#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
import time
import subprocess
import re
import uuid

FEISHU_APP_ID = "cli_aa9aaaa1b07adcd7"
FEISHU_APP_SECRET="xeqqHL5rbstAsvDSw74Anf8Ll6hDdG8B"
CHAT_ID = "oc_43f017d2dd025b2fa6dc3633f07ab788"
OPENCLAW_APP_ID = "cli_aa9aa99d997a1ccd"
API_KEY="sk-d290ae08640740c387c441893393321f"
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "MiniMax-M2.5"

SYSTEM_PROMPT = "你是 Hermes Agent，AI协作系统的执行引擎。你是 OpenClaw 的下属，职责是执行 OpenClaw 派发的技术任务并汇报结果。汇报格式：【执行结果】- 命令: xxx - 状态: 成功/失败 - 输出: xxx - 总结: xxx。保持简洁务实。"

token = None
token_expire = 0
processed = set()
LOG_FILE = "/root/hermes_reply.log"

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except:
        pass

def get_token():
    global token, token_expire
    if token and time.time() < token_expire - 300:
        return token
    r = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10)
    d = r.json()
    if d.get("code") == 0:
        token = d["tenant_access_token"]
        token_expire = time.time() + d.get("expire", 5400)
        log("[Token] OK")
        return token
    log("[Token] FAIL")
    return None

def get_messages():
    t = get_token()
    if not t: return []
    params = {"container_id_type": "chat", "container_id": CHAT_ID, "page_size": 10, "sort_type": "ByCreateTimeDesc"}
    try:
        r = requests.get("https://open.feishu.cn/open-apis/im/v1/messages",
            headers={"Authorization": "Bearer " + t}, params=params, timeout=10)
        d = r.json()
        if d.get("code") == 0:
            items = d.get("data", {}).get("items", [])
            log(f"[Msgs] {len(items)}")
            return sorted(items, key=lambda x: x.get("create_time", "0"))
    except Exception as e:
        log(f"[Msgs] ERR: {e}")
    return []

def extract_text(msg):
    try:
        return json.loads(msg.get("body", {}).get("content", "{}")).get("text", "")
    except:
        return ""

def get_sender_id(msg):
    sender = msg.get("sender", {})
    return sender.get("id", "")

def extract_command_from_openclaw(text):
    match = re.search(r"执行命令:\s*(.+)", text)
    if match:
        cmd = match.group(1).strip()
        if cmd and len(cmd) < 200:
            log(f"[Extract] from 执行命令: {cmd[:50]}")
            return cmd
    
    code_blocks = re.findall(r"```(?:bash\r?\n)?(.+?)```", text, re.DOTALL)
    if code_blocks:
        cmd = code_blocks[0].strip()
        for p in ["执行命令:", "cmd:", "command:", "$ "]:
            if cmd.startswith(p):
                cmd = cmd[len(p):].strip()
        if cmd and len(cmd) < 200:
            log(f"[Extract] from code block: {cmd[:50]}")
            return cmd
    
    match = re.search(r"`([^`]+)`", text)
    if match:
        cmd = match.group(1).strip()
        if cmd and len(cmd) < 200:
            log(f"[Extract] from backtick: {cmd[:50]}")
            return cmd
    
    return None

def check_hermes(msg, text):
    sender_id = get_sender_id(msg)
    tl = text.lower().strip()
    
    if tl.startswith("@hermes"):
        return True
    
    try:
        for m in msg.get("mentions", []):
            name = m.get("name", "").lower()
            if "hermes" in name and "bot" in name:
                return True
    except:
        pass
    
    if sender_id == OPENCLAW_APP_ID:
        import re
        if re.search(r"```.+?```", text, re.DOTALL):
            return True
    
    return False

def call_ai(text):
    try:
        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        data = {"model": MODEL, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}], "max_tokens": 500}
        r = requests.post(f"{API_URL}/chat/completions", headers=headers, json=data, timeout=60)
        result = r.json()
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        log(f"[AI] ERR: {e}")
        return None

def send_reply(text):
    t = get_token()
    if not t: return
    try:
        r = requests.post(f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
            headers={"Authorization": "Bearer " + t, "Content-Type": "application/json"},
            json={"receive_id": CHAT_ID, "msg_type": "text", "content": json.dumps({"text": text})}, timeout=10)
        d = r.json()
        msg = "OK" if d.get("code")==0 else "FAIL"
        log(f"[Reply] {msg}")
    except Exception as e:
        log(f"[Reply] ERR: {e}")

def execute_command(cmd, max_retries=2):
    task_id = str(uuid.uuid4())[:8]
    
    for attempt in range(max_retries + 1):
        log(f"[Execute] 尝试 {attempt + 1}/{max_retries + 1}: {cmd[:40]}")
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            out = result.stdout or result.stderr
            
            if result.returncode == 0:
                if len(out) > 300:
                    out = out[:300] + "...(截断)"
                return {
                    "task_id": task_id,
                    "success": True,
                    "cmd": cmd,
                    "output": out[:200],
                    "attempt": attempt + 1
                }
            else:
                log(f"[Execute] 命令失败 (exit code: {result.returncode})")
                if attempt < max_retries:
                    log(f"[Execute] 5秒后重试...")
                    time.sleep(5)
        except subprocess.TimeoutExpired:
            log(f"[Execute] 命令超时")
            if attempt < max_retries:
                time.sleep(5)
        except Exception as e:
            log(f"[Execute] 异常: {e}")
            if attempt < max_retries:
                time.sleep(5)
    
    return {
        "task_id": task_id,
        "success": False,
        "cmd": cmd,
        "output": out[:200] if "out" in dir() else "执行失败",
        "attempt": max_retries + 1
    }

def format_report(exec_result):
    status = "SUCCESS" if exec_result["success"] else "FAILED"
    output_summary = exec_result.get("output", "")[:80] if exec_result.get("output", "") else "无输出"
    
    task_id = exec_result["task_id"]
    report = f"\n[Report: {task_id} | {status} | {output_summary}]"
    return report

def main():
    log("=" * 20 + " Hermes V3 " + "=" * 20)
    while True:
        try:
            for msg in get_messages():
                mid = msg.get("message_id", "")
                if mid in processed:
                    continue
                text = extract_text(msg)
                sender_id = get_sender_id(msg)
                processed.add(mid)
                if not text:
                    continue
                
                if check_hermes(msg, text):
                    log(f"[Trigger] {mid[:20]} (sender: {sender_id})")
                    
                    is_from_openclaw = (sender_id == OPENCLAW_APP_ID)
                    
                    if is_from_openclaw:
                        cmd = extract_command_from_openclaw(text)
                        if cmd:
                            log(f"[OpenClaw] extracted: {cmd[:50]}")
                        else:
                            cmd = text.replace("@Hermes", "").replace("@hermes", "").replace("Bot", "").replace("bot", "").replace("执行命令:", "").strip()
                    else:
                        cmd = text.replace("@Hermes", "").replace("@hermes", "").replace("Bot", "").replace("bot", "").strip()
                    
                    if cmd and len(cmd) > 1 and len(cmd) < 200:
                        exec_result = execute_command(cmd, max_retries=2)
                        
                        status = "OK" if exec_result["success"] else "FAIL"
                        out_str = str(exec_result.get("output", ""))[:100]
                        reply = f"[Execute] Cmd: {cmd[:40]} | Status: {status} | Output: {out_str}"
                        
                        reply += format_report(exec_result)
                    else:
                        reply = call_ai(text)
                    if reply:
                        send_reply(reply)
            time.sleep(5)
        except Exception as e:
            log(f"[Main] {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
