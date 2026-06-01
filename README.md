# AI Team Collaboration System

飞书群聊 AI 助手双 Agent 系统 - OpenClaw (主控) + Hermes (执行)

## 项目结构

```
ai-projects/
├── feishu_reply.py      # OpenClaw 主控 Agent (飞书消息处理 + AI 调度)
├── hermes_reply.py      # Hermes 执行 Agent (命令执行 + 结果汇报)
├── README.md            # 项目说明
└── .git/                # Git 版本控制
```

## 功能说明

### OpenClaw (feishu_reply.py)
- 监听飞书群聊消息
- AI 模型调用 (阿里云百炼 MiniMax-M2.5)
- 任务规划和指令派发
- 执行结果分析和下一步决策

### Hermes (hermes_reply.py)
- 监听群聊中的执行指令
- 执行系统命令 (subprocess)
- 命令失败自动重试 (最多 2 次)
- 标准化结果汇报 [Report: xxx | SUCCESS/FAILED | output]

## 协作流程

1. 用户发送需求 → OpenClaw 分析并规划
2. OpenClaw 用 ```shell 代码块 格式指派 Hermes
3. Hermes 执行命令，返回 [Report:] 标签
4. OpenClaw 解析报告，决定下一步或汇报完成

## 技术栈

- 飞书开放平台 API
- 阿里云百炼 (MiniMax-M2.5)
- Python 3
- Git 版本控制
- systemd 服务管理

## 配置

- 飞书 App ID/Secret
- 阿里云 API Key
- 群聊 Chat ID

## 部署方式

### screen (开发/调试)
```bash
screen -dmS reply python3 /root/feishu_reply.py
screen -dmS hermes python3 /root/hermes_reply.py
```

### systemd (生产环境)
```bash
systemctl enable feishu-reply hermes-reply
systemctl start feishu-reply hermes-reply
```

## 版本

v1.0.0 - 基础双 Agent 协作系统
