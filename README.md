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

截至 2026-09-26，已整理构想、系统流程、数据接口、实验设计及参赛材料框架；**仍处于设计阶段，尚未实现原型或完成实验**。新增 JSON 为虚构说明样例。

建议先阅读操作流程，再看程序框架、数据协议和实施路线；准备交件时以参赛材料框架逐项核对。内部设计文档使用中文，正式提交及演示使用英文。下一步验证最核心的问题：

> **How much of an adaptive AI tutor can be compiled into paper, and how infrequently does AI need to appear while still preserving meaningful personalization?**
