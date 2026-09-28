# PAPER AI 项目构想

> **文档分类：总括性文档。** 更新：2026-09-28。本文描述当前 0.5 之后的项目概念，不把旧版固定分流机制当成项目本体。

## 1. 一句话定义

**PAPER AI 是一种“间歇式 AI 教育”框架：AI 在有限接入时段内理解学习证据并设计下一段教学，把内容、反馈与下一步策略编译进纸质媒体；学生随后可以数天离线学习，最后再把纸面轨迹交还 AI 更新下一轮。**

英文工作标题：**PAPER AI: Compiling Adaptive AI Education into Paper**

核心闭环：

```text
AI → Paper → Human → Paper Trace → AI
```

## 2. 它解决什么问题

多数 AI Tutor 默认学生持续拥有网络、设备、电力和模型访问。PAPER AI 研究另一种假设：

> **AI 不需要一直在场，个性化教学仍可以继续。**

适用场景既包括资源有限、网络/设备不稳定的教育环境，也包括希望降低学生屏幕依赖但保留个性化教学的普通学校环境。

## 3. “纸”不是普通 worksheet

项目的创新边界不是“AI 自动出题并打印”，而是把一段**教学策略**也放进纸里：

- AI 先讲解并设计多个题组；
- 每组完成后，核对册提供针对表现的反馈和下一步指导；
- 指导可以依据正确数、具体错题、知识点理解或其组合；
- 提示、重试和首次答案分别记录；
- 未分配的题组可以保持空白；
- 最终记录纸被扫描、人工校对并转成下一轮证据。

0.5 的重要变化是：**教学策略不再被强行压成固定 score/rule 模板。** AI 可以写自然语言的纸上指导，程序只做最小结构/引用检查，教师审核教学合理性。这样保留 AI Tutor 的灵活判断，同时保证纸张在无 AI 时仍有可执行说明。

## 4. 一个例子

AI 预先打印三组材料：诊断/基础、针对性补强、应用/进阶。学生完成第一组后才打开核对册。核对册可以写：

- 若关键概念题 Q2/Q5 出错，先进入第 2 组补强；
- 若概念题稳定但应用题才出错，可直接进入第 3 组；
- 若达到目标则结束；
- 若需要重访某组，明确重做什么以及何时停止。

这些文字在开始前已经印好；中途没有网络、AI 调用或教师补发材料。最后教师扫描全部记录，确认哪些组确实未被分配，AI 再基于首次答案、提示/重试和确认记录生成学情总结与下一轮。

## 5. 核心研究问题

1. **How much of an adaptive AI tutor can be compiled into paper?**
2. **How infrequently can AI appear while preserving meaningful personalization?**
3. 哪些教学判断适合预先写入纸张，哪些必须等待下一次 AI 接入？
4. 自然语言离线指导是否足够清楚，让学生在没有 AI 时正确执行？
5. 纸面轨迹能恢复哪些学习事实，哪些必须由教师确认？
6. 与静态 worksheet 和持续在线 AI Tutor 相比，PAPER AI 的学习效果、教师负担、设备时间和成本如何？

## 6. AI、程序与教师的分工

**AI：**依据目标、背景和已确认证据生成讲解、题目、提示、解析、题组策略、学情总结和下一轮调整。

**程序：**保存版本、检查 JSON/题号/答案字段、排版 Markdown、生成 PDF/记录纸、识别 OMR、保存首次/重试/提示与 confirmed skipped 状态、管理 provider 协议。

**教师：**审核事实正确性、答案与难度、自然语言指导是否可执行，以及扫描后的真实未分配题组。程序不假装理解或证明任意自然语言教学策略。

## 7. Paper Compiler 与 Paper Trace

```text
Student Evidence
→ AI Lesson/Workbook Authoring
→ Structural Validation
→ Teacher Review
→ Paper Compiler
→ Booklet + Check Booklet + Record Sheets + Teacher Guide
```

```text
Record Sheets
→ OMR / Manual Review
→ Confirmed Trace
→ Evaluation
→ AI Learning Summary
→ Next Round
```

## 8. 当前原型 0.5

当前已实现自定义主题、2–3 组×5–10 题、Markdown、自然语言自由指导、多页记录、面积式 OMR、直接 PDF 下载、中英界面、学情总结和多协议 provider 网关。

已有一次真实 DeepSeek 默认 3×10（30 题）工程生成成功记录；其他平台主要是协议模拟。0.5 的浏览器视觉、真实 PDF、原失败照片扫描和自然语言纸上可用性仍需新版复测。

## 9. 研究与声明边界

PAPER AI 当前不能宣称：任意学科无需教师审核、所有支持平台均已真实验证、合成扫描代表实拍准确率、工程可运行即证明学习增益、已找到最低有效 AI 接入频率，或“分支纸张”本身是首创。

> **Teaching strategy can be prepared with AI, continue on paper while AI is absent, and return as evidence for the next adaptive round.**

## 10. 赛道定位

目前最自然的定位仍是 **AI for Less Developed Countries**，因为项目直接降低持续联网和学生设备需求；也可从 **AI for Education** 角度强调低屏幕、纸媒与 AI 协同的个性化学习。最终只选择一个参赛组别。

### 核心标语

> **What if AI could work even when AI is gone?**

> **Plan once with AI. Learn for days on paper. Return with evidence.**
