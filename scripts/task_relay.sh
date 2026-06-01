#!/bin/bash
# AI任务中继脚本 - 每60秒检查任务队列

QUEUE_FILE="/opt/ai-office/task-queue.md"
LOG_FILE="/opt/ai-office/logs/task_relay.log"
CHECK_INTERVAL=60

# 加载配置
source /opt/ai-office/config/keys.env

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

send_report() {
    python3 /opt/ai-office/scripts/send_report.py "$1"
}

# 获取飞书token
get_feishu_token() {
    curl -s -X POST 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'         -H 'Content-Type: application/json'         -d "{\"app_id\": \"\", \"app_secret\": \"\"}" |         python3 -c "import json,sys; print(json.load(sys.stdin).get('tenant_access_token',''))"
}

log "任务中继脚本已启动"
send_report "AI任务监听器已启动，每60秒检查一次任务队列"

while true; do
    # 检查任务队列
    if [ -f "$QUEUE_FILE" ]; then
        # 查找待执行任务
        PENDING_TASK=$(grep -A 1 '## 待执行任务' "$QUEUE_FILE" | grep -v '## 待执行任务' | grep -v '暂无' | head -1)
        
        if [ -n "$PENDING_TASK" ]; then
            log "发现新任务: $PENDING_TASK"
            
            # 提取任务内容（去掉[待执行]前缀）
            TASK_CONTENT=$(echo "$PENDING_TASK" | sed 's/\[待执行\] //')
            
            # 记录开始执行
            TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
            sed -i "s/${PENDING_TASK}/[进行中] ${TASK_CONTENT}/" "$QUEUE_FILE"
            
            log "开始执行任务: ${TASK_CONTENT}"
            send_report "开始执行任务: ${TASK_CONTENT}"
            
            # 执行任务（这里可以添加具体的任务执行逻辑）
            # TODO: 根据任务类型调用不同的执行器
            
            # 任务完成后标记为已完成
            sed -i "s/\[进行中\] ${TASK_CONTENT}/[已完成] ${TASK_CONTENT}/" "$QUEUE_FILE"
            
            log "任务完成: ${TASK_CONTENT}"
            send_report "任务已完成: ${TASK_CONTENT}"
        fi
    fi
    
    sleep $CHECK_INTERVAL
done
