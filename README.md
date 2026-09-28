> 当前版本 **0.6**：首页概论 + 三工作区、实拍编码偏移修复、提示勾选框与答题括号。查看 [当前进度](docs/product_06_status.md)、[人工指南](docs/manual_operation_guide.md)、[本地验收](docs/local_ai_test_guide.md)。

# UNUAI — PAPER AI

> **文档分类：总括性文档。** 当前版本：**0.6**（2026-09-28）。完整文档分类见 [docs/README.md](docs/README.md)。

本仓库用于准备 **2026 全球青少年人工智能未来创新竞赛（澳门中学生赛区）** 的 PAPER AI 项目。

## 项目一句话

**PAPER AI: Compiling Adaptive AI Education into Paper**

AI 在有限的接入时段内分析学生、设计教学内容与下一步指导，并把未来一段时间的个性化学习策略编译成可以脱离网络和学生设备独立运行的纸质学习包；学习结束后再扫描纸面记录，更新学生状态并生成下一轮。

```text
AI → Paper → Human → Paper Trace → AI
```

当前版本不再把“自适应”限制为死板的机器分流规则。AI 可以在核对册中写自然语言指导，例如根据正确数、特定错题或知识点表现决定补强、进阶、回看或结束；程序只验证题目/组号引用等最小结构，教师负责审核教学逻辑。

## 当前 Demo 0.5

```text
教师自定义主题
→ AI 讲解 + 2–3 个题组（每组 5–10 题）+ 离线指导
→ 教师审核/冻结
→ 题册 + 核对册 + 记录纸 + 教师版
→ 学生整组作答后核对并按纸面指导继续
→ 最后统一拍照/扫描
→ 人工校对与确认未分配题组
→ AI 学情总结
→ 同主题下一轮
```

主要新增能力包括 Markdown 内容、本机 Chrome/Edge 直接 PDF 导出、面积式 OMR、多页记录、中英界面，以及 OpenAI Responses、Azure Responses、Claude Messages、Gemini generateContent、DashScope 和 Chat Completions 等协议适配。**协议适配/模拟通过不等于所有平台都已用真实密钥验证。**

启动：

```bash
python demo/launch.py
```

浏览器打开 `http://127.0.0.1:8765`；Windows 也可双击 `demo/start-demo.bat`。

## 先看这几份

- [文档总索引：总括 / 当前 / 历史](docs/README.md)
- [0.5 实现与验证状态](docs/product_05_status.md)
- [0.5 人工操作指南](docs/manual_operation_guide.md)
- [0.5 本地 AI 测试与验收要求](docs/local_ai_test_guide.md)
- [项目构想](docs/project_idea.md)
- [当前实施路线](docs/implementation_roadmap.md)

## 当前证据边界

0.5 已记录 **47 项 Python 自动检查通过**，并有一次真实 DeepSeek 中文默认 3×10（30 题）自由指导学习包生成成功的工程记录。上一版人工实测已经完成并促成 0.5 六项修订，但 **0.5 自身的新 PDF、面积扫描、自由指导与多平台改动仍需按新版指南复测**。

不能把以下内容写成已证明：

- 协议模拟 = 所有平台真实调用稳定；
- 合成扫描 = 实拍扫描准确率；
- 工程包生成成功 = 任意学科内容正确；
- 纸面流程可运行 = 已证明学习增益；
- 短期测试 = 已找到最低有效 AI 接入频率。

当前最核心研究问题仍是：

> **How much of an adaptive AI tutor can be compiled into paper, and how infrequently does AI need to appear while still preserving meaningful personalization?**

本次更新：优化生成提示词和局部反馈修复，统一双语排版，预留一文一理展示题库。通用知识单元内容扩展已取消。
