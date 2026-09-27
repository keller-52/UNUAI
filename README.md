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

当前 Demo 0.4 支持教师自定义主题、AI 先讲解后出题、每组 5–10 题的整批核对与离线分流、多页记录，以及基于已确认记录的学情总结与下一轮生成。

建议按以下顺序使用：

- [0.4 人工操作指南](docs/manual_operation_guide.md)
- [0.4 本地 AI 测试与验收要求](docs/local_ai_test_guide.md)
- [0.4 当前实现与验证状态](docs/product_04_status.md)

本地单教师 Demo 使用 Python 3.10+，运行应用无需安装额外 Python 依赖：

```bash
python demo/launch.py
```

打开 **http://127.0.0.1:8765**。Windows 可双击 `demo/start-demo.bat`。

自定义主题需要配置真实 AI；规则演示只用于兼容与工程测试，不能冒充真实 AI 结果。所有离线题组、核对内容和记录纸应在开始前一次打印，学生完成整组后再核对并按预先设计的规则进入下一题组，中途无需联网或再次调用 AI。

## 文档

- [竞赛章程整理](docs/competition_rules.md)
- [PAPER AI 项目构想](docs/project_idea.md)
- [0.4 人工操作指南](docs/manual_operation_guide.md)
- [0.4 本地 AI 测试与验收要求](docs/local_ai_test_guide.md)
- [0.4 当前实现与验证状态](docs/product_04_status.md)
- [程序框架与模块职责](docs/system_architecture.md)
- [完整操作流程与纸张设计](docs/operation_workflow.md)
- [数据协议与 AI 接口](docs/data_contracts.md)
- [自主出题协议](docs/ai_question_authoring.md)
- [JSON 往返示例](examples/round_trip.json)
- [研究问题、实验与证据计划](docs/research_plan.md)
- [参赛材料内容框架](docs/submission_framework.md)
- [实施路线与任务清单](docs/implementation_roadmap.md)
- [0.2 历史验收报告](docs/local_validation_02_results.md)
- [0.2 历史实物检测指南](docs/manual_physical_validation.md)
- [人工实物检测记录模板](docs/manual_physical_test_record.md)

## 当前阶段

截至 2026-09-27，0.4 已有 **42 项自动检查通过**记录，并完成一次真实 DeepSeek 15 题离线分流包与一次学情总结的工程验证。

仍未完成的当前版验收包括：0.4 浏览器 / PDF 复测、默认 30 题、多主题与中英文真实 AI 稳定性、真实打印填写与手机多页扫描闭环，以及学情总结到下一轮的完整实物证据。0.2 的浏览器 / PDF 通过结果只作为历史基线，不能代替 0.4 复测。

明确延期：各大主流平台原生 API 适配、正式展示用两个较难文 / 理知识点的最终选择，以及更长期的学习效果 / AI 接入间隔研究。

合成作答、规则演示和工程测试均不能证明真实学习效果。详细 PASS / FAIL / BLOCKED / NOT RUN 口径见 [本地 AI 测试与验收要求](docs/local_ai_test_guide.md)。

下一步验证最核心的问题仍是：

> **How much of an adaptive AI tutor can be compiled into paper, and how infrequently does AI need to appear while still preserving meaningful personalization?**
