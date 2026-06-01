#!/bin/bash
# Skill自动总结脚本
# 用法: ./save_skill.sh <任务名称> <日志文件路径>

set -e

SKILL_DIR="/opt/ai-office/skills"
LOG_FILE="$2"
TASK_NAME="$1"

if [ -z "$TASK_NAME" ] || [ -z "$LOG_FILE" ]; then
    echo "用法: $0 <任务名称> <日志文件路径>"
    exit 1
fi

SKILL_FILE="${SKILL_DIR}/${TASK_NAME}.md"

echo "正在分析日志: $LOG_FILE"

# 分析日志，提取关键信息
TASK_DESC=$(head -5 "$LOG_FILE" 2>/dev/null | grep -v '^#' | head -1)
EXTRACTED_COMMANDS=$(grep -E '^\$|sudo |curl |ssh |python' "$LOG_FILE" 2>/dev/null | head -20 | sed 's/^[[:space:]]*//')
ERRORS=$(grep -iE 'error|fail|denied|blocked' "$LOG_FILE" 2>/dev/null | head -10)
SOLUTIONS=$(grep -iE 'fix|solve|workaround|retry|sed|patch' "$LOG_FILE" 2>/dev/null | head -10)

# 生成Skill文件
cat > "$SKILL_FILE" << EOF
# Skill: $TASK_NAME

## 任务描述
$TASK_DESC

## 执行步骤

### 1. 准备阶段
- 分析任务需求
- 检查环境依赖

### 2. 执行阶段
```bash
# 关键命令
$EXTRACTED_COMMANDS
```

### 3. 验证阶段
- 检查执行结果
- 确认输出符合预期

## 注意事项
- 常见错误及解决方案
$ERRORS

## 有效命令
```
$EXTRACTED_COMMANDS
``"

## 解决方案记录
$SOLUTIONS

---
Skill版本: 1.0
创建时间: $(date '+%Y-%m-%d %H:%M:%S')
EOF

echo "Skill已保存: $SKILL_FILE"

# 提交到GitHub
cd /opt/ai-office
git add skills/
git commit -m "Add skill: $TASK_NAME" 2>/dev/null || echo "无需提交"
git push origin main 2>/dev/null || echo "推送失败"

echo "完成!"
