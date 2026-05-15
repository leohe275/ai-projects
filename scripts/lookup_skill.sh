#!/bin/bash
# Skill查找脚本 - 用于在执行任务前检查是否有相关经验
# 用法: ./lookup_skill.sh <关键词>

SKILL_DIR="/opt/ai-office/skills"
KEYWORD="$1"

if [ -z "$KEYWORD" ]; then
    echo "用法: $0 <关键词>"
    echo ""
    echo "可用Skills:"
    ls -1 "$SKILL_DIR"/*.md 2>/dev/null || echo "暂无Skills"
    exit 0
fi

# 搜索相关Skill
echo "=== 搜索关键词: $KEYWORD ==="
RESULTS=$(grep -l -i "$KEYWORD" "$SKILL_DIR"/*.md 2>/dev/null)

if [ -z "$RESULTS" ]; then
    echo "未找到相关Skill，将从头开始执行"
    exit 1
else
    echo "找到相关经验:"
    for file in $RESULTS; do
        echo ""
        echo "-----------------------------------"
        echo "文件: $file"
        echo "-----------------------------------"
        head -30 "$file"
    done
    echo ""
    echo "建议: 请先查阅以上Skills，参考成功经验"
fi
