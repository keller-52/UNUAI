# UNUAI

本仓库用于准备 **2026 全球青少年人工智能未来创新竞赛（澳门中学生赛区）** 项目。

## 当前项目：PAPER AI

**PAPER AI — Compiling Adaptive AI Education into Paper**

核心思想：让 AI 不必持续在线，而是在有限的联网/设备使用时段内理解学生、规划教学，并把未来一段时间的个性化教学策略“编译”成可独立运行的纸质媒体。学生离线学习后，纸面留下学习轨迹；下一次接入 AI 时，系统再根据这些轨迹更新下一轮纸质学习包。

核心闭环：

```text
AI → Paper → Human → Paper Trace → AI
```

这不是“AI 生成 worksheet”，而是研究一种 **Intermittent AI Education（间歇式 AI 教育）**：AI 只在关键节点出现，纸张承担中间时段的教学逻辑与学习记录。

## 当前赛道定位

PAPER AI 最自然地对应：

- **AI for Less Developed Countries｜人工智能支援欠发达地区**：适用于网络、电力、设备不稳定或不足的地区。

如果后续决定坚持 **AI for Education｜人工智能促进教育**，也可以把研究重点调整为：

- 低屏幕、低设备依赖的个性化学习；
- AI 与纸质媒体协同的新型教学模式；
- AI 出现频率与个性化学习效果之间的关系。

最终参赛组别将在项目方案进一步确定后锁定。

## 运行 Demo

已加入本地单教师 Demo 0.1，使用 Python 3.10+，无需安装运行依赖：

```bash
python demo/server.py
```

打开 **http://127.0.0.1:8765**。Windows 可双击 `demo/start-demo.bat`。

包含基础诊断、教学规划、审核打印、独立记录纸、本地选框扫描、校对评价和第二轮更新。无 API 密钥可用明确标识的规则演示；真实 AI 需自行配置服务。

- [启动与操作说明](demo/README.md)
- [实现范围与验证状态](docs/demo_status.md)
- [给本地 AI 的验证交接](docs/local_validation_handoff.md)

## 文档

- [竞赛章程整理](docs/competition_rules.md)
- [PAPER AI 项目构想](docs/project_idea.md)
- [程序框架与模块职责](docs/system_architecture.md)
- [完整操作流程与纸张设计](docs/operation_workflow.md)
- [数据协议与 AI 接口](docs/data_contracts.md)
- [JSON 往返示例](examples/round_trip.json)
- [研究问题、实验与证据计划](docs/research_plan.md)
- [参赛材料内容框架](docs/submission_framework.md)
- [实施路线与任务清单](docs/implementation_roadmap.md)

## 当前阶段

截至 2026-09-26，已加入 **Demo 0.1 代码**，包含本地教学闭环与测试。真实 AI 外部调用、实际打印拍照和真人教育实验仍待完成；已跑与待跑检查见 [实现状态](docs/demo_status.md)。`examples/round_trip.json` 仍是虚构协议说明样例。

建议先阅读操作流程，再看程序框架、数据协议和实施路线；准备交件时以参赛材料框架逐项核对。内部设计文档使用中文，正式提交及演示使用英文。下一步验证最核心的问题：

> **How much of an adaptive AI tutor can be compiled into paper, and how infrequently does AI need to appear while still preserving meaningful personalization?**
