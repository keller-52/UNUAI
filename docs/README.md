> 当前实现以 [0.6 进度](product_06_status.md)、[本地验收](local_ai_test_guide.md)、[人工指南](manual_operation_guide.md) 为准。0.5 进度属于上一版本实现记录，平台表继续适用。

# UNUAI 文档索引

> **文档分类：总括性文档。** 更新：2026-09-28。当前产品版本为 **PAPER AI 0.5**，代码实现基线为 `4e04b620352db32f9237368a69bcb1fa12dde6a7`。
> 本页是仓库文档的唯一分类入口。历史文档保留用于追溯，不应拿来替代当前操作或验收要求。

## 1. 总括性文档

| 文档 | 用途 |
|---|---|
| [仓库首页](../README.md) | 项目总入口、当前版本与最重要链接 |
| [PAPER AI 项目构想](project_idea.md) | 核心概念、创新边界与研究问题 |
| [2026 竞赛章程整理](competition_rules.md) | 当前澳门赛区规则摘要；以官方原文为准 |
| [研究问题、实验与证据计划](research_plan.md) | 工程、可用性与教育效果证据如何取得 |
| [参赛材料内容框架](submission_framework.md) | Project Introduction、Research Report、Poster、Video 的事实框架 |
| [实施路线与任务清单](implementation_roadmap.md) | 从 0.5 复测到交件的当前 To-do |

## 2. 当前文档（0.5）

| 文档 | 当前职责 |
|---|---|
| [0.5 实现与验证状态](product_05_status.md) | 六项实测反馈后的功能、证据与限制 |
| [0.5 人工操作指南](manual_operation_guide.md) | 下载、配置、生成、审核、PDF、纸上学习、扫描 |
| [0.5 本地 AI 测试与验收要求](local_ai_test_guide.md) | 自动测试、真实 AI、浏览器/PDF、实物复测 |
| [0.5 实物复测记录模板](manual_physical_test_record.md) | 人工真值、照片、扫描、打印问题记录 |
| [当前系统架构](system_architecture.md) | 0.5 实际模块、AI/程序/教师职责边界 |
| [当前操作流程与纸张设计](operation_workflow.md) | 整批作答、自然语言指导、最终扫描闭环 |
| [当前数据协议](data_contracts.md) | 自定义主题、自由指导、trace/evaluation/provider 的当前语义 |
| [本地 AI 测试交接](local_validation_handoff.md) | 当前测试执行的短入口 |
| [Demo README](../demo/README.md) | 代码目录、启动、配置与开发者测试入口 |

**当前路由原则：**AI 可以自由设计答案册中的自然语言反馈与下一步指导；不再要求 targeted rule 必须在 score fallback 前，也不要求分数区间穷尽、首组固定两个去向、只向后跳或所有组均可达。程序只做最小结构/引用检查，教学逻辑由教师审核。自由指导包的空白题不会被程序自动解释为错误或自动重建路线；教师确认真正未分配的题组后再保存。

## 3. 历史文档

| 文档 | 历史范围 |
|---|---|
| [0.1 本地验证结果](local_validation_results.md) | 早期 Windows/浏览器修复记录 |
| [DeepSeek 接入与验证](deepseek_validation.md) | 早期 DeepSeek 单提供商接入记录 |
| [0.2 实现记录](product_02_status.md) | 2–4 题、单页 OMR 阶段 |
| [0.2 本地验收](local_validation_02_results.md) | 0.2 的软件/PDF/DeepSeek 验收证据 |
| [旧进度报告](demo_status.md) | 0.2 为主的阶段性状态 |
| [0.2 人工实物检测指南](manual_physical_validation.md) | 旧三题/单页/固定路径实物流程 |
| [0.3 AI 自主出题协议](ai_question_authoring.md) | 旧固定方程单元生成契约 |
| [0.4 自定义主题与固定分流](product_04_status.md) | 强规则排序和分数兜底阶段 |
| [0.4 验收入口兼容页](local_validation_04_requirements.md) | 指向 0.5 的兼容入口 |
| [旧知识单元扩展接口](unit_extension_contract.md) | 固定 `linear-equations` 单元/旧 OMR 容量设计 |

## 4. 运行资产，不作为说明文档

- `demo/prompts/custom_workbook.md`：0.5 自定义主题与自由指导提示词。
- `demo/prompts/learning_summary.md`：学情总结提示词。
- `demo/prompts/author_lesson.md`：旧固定单元仍使用的兼容提示词。

`examples/round_trip.json` 是早期协议示例，不代表 0.5 自定义主题的完整当前数据结构。

## 5. 当前事实基线

- 0.5 已实现：自定义主题、每组 5–10 题/2–3 组、Markdown 教学内容、AI 自然语言离线指导、多页记录、面积式 OMR、直接 PDF 导出、多协议/多平台配置、学情总结与下一轮。
- 自动化：0.5 已记录 47 项 Python 检查通过；前端语法、合成扫描、Markdown 与协议模拟已有工程检查。
- 真实 AI：已有 DeepSeek `deepseek-flash` 中文默认 3×10（30 题）工程生成成功记录；这不是跨主题/跨平台稳定率证明。
- 仍需复测：0.5 浏览器视觉与真实 PDF、一键 PDF 在不同电脑上的表现、原失败照片与新面积阈值、真实多页扫描、中英文长内容，以及自然语言指导的纸上可用性。
- 其他平台：接口/协议模拟不等于真实账号调用通过；无对应密钥时应记为 NOT RUN。
- 教育效果、长期保持、最低有效 AI 接入频率尚未证明。

以后每次核心功能改变时，至少同步：当前版本状态页、`manual_operation_guide.md`、`local_ai_test_guide.md`、本索引及根 `README.md`。
