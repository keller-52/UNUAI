# PAPER AI 当前系统架构

> **文档分类：当前文档。** 更新：2026-09-28。对应 0.5 实现基线 `4e04b620352db32f9237368a69bcb1fa12dde6a7`。实际代码优先于本文。

## 1. 当前部署边界

Demo 是**本机单教师应用**：Python 标准库 HTTP 服务 + SQLite + 原生浏览器前端。默认只监听 localhost。学生可以完全只使用纸张；AI 调用、审核、PDF 与扫描由教师电脑完成。

```text
Teacher UI
   ├─ Student / Topic / Evidence
   ├─ AI Provider Gateway ── Remote Model
   ├─ Workbook Validator
   ├─ Paper / Markdown Renderer
   ├─ Local PDF Export ── Chrome/Edge
   ├─ OMR Scanner + Manual Review
   └─ SQLite / Backup
```

## 2. 当前模块

| 文件/模块 | 当前职责 |
|---|---|
| `server.py` | HTTP API、SQLite、生成任务、学习包、trace、summary、PDF 下载 |
| `providers.py` | Chat/Responses/Azure/Anthropic/Gemini/DashScope 六类协议 |
| `workbook.py` | 自定义主题 proposal、自由 guidance、trace/evaluation |
| `core.py` | 公共状态、旧固定单元兼容、基础校验 |
| `pdf_export.py` | 调用本机 Chrome/Edge headless 生成真正 PDF |
| `static/workbook.js` | 自定义题册/核对册与 Markdown 安全渲染 |
| `static/paper.js` | 记录纸、教师版、分页/打印兼容 |
| `static/scanner.js` | 四角定位、透视、sheet code、面积式 OMR |
| `static/app.js` | 教师工作流、provider、校对、confirmed skipped |
| `persistence.py` | 备份/恢复与数据一致性 |
| `prompts/*.md` | 运行时 AI 系统提示词 |

## 3. AI / 程序 / 教师职责

### AI

AI 可以自由决定如何讲解、题目与难度、哪些错误值得针对、每个题组后的自然语言反馈，以及去补强、进阶、回看、重做或结束的条件。

### 程序

程序只做能可靠确定的事情：JSON/字段存在性、Q1..Qn、四选项与 correct_option、hint 数量、题组数量/题量、guidance 中显式 Q/组号越界检查、旧 rules 基本兼容、内容长度/版本/冻结、PDF/记录纸、OMR、provider 协议。

**程序不再要求** targeted-first、score fallback 全覆盖、首组至少两个目的地、只能向后跳、无环或全组可达，也不声称自动理解任意自然语言指导。

### 教师

教师审核事实、答案、解释、难度、guidance 是否清楚且有停止条件、纸张可读性、扫描校对，以及哪些空白题组确实未被分配。

## 4. 当前自定义学习包

```text
title / reason / learning_summary / evidence_refs
lesson[]
questions[Q1..Qn]
batch_feedback[{ batch, title, focus, guidance }]
```

`guidance` 是学生完成整个题组并核对首次答案后阅读的 Markdown。旧 `rules[]` 仍可加载作为兼容格式，但不是当前主设计。

编译后 `routing_version=free-guidance-1`。题目节点顺序排列；真正的题组选择由纸面 guidance 和学生执行决定，而不是后台偷偷替学生运行自然语言。

## 5. 纸质输出

当前四类输出：讲解与题册、提示/答案/核对册、多页 OMR 记录纸、教师答案指南。

Markdown 本地渲染标题、段落、粗体、列表、代码和简单表格；不执行 AI HTML/脚本/链接，不宣称完整 LaTeX。

打印有两条路径：浏览器 `window.print()` / Ctrl+P，以及 0.5 服务端调用本机 Chrome/Edge headless 的直接 PDF。

## 6. Paper Trace

记录纸每页最多 8 题，保存 first_answer、hint_level、retry_answer 和 sheet/package/page identity。0.5 面积式 OMR 使用局部纸色与圆圈内采样判断明显填涂；多选/不确定保留 unknown。

自由 guidance 模式不自动重建路线。空白题为 `unanswered_or_skipped`；只有教师确认某题组确实未被分配，才保存 `skipped_batches` 并标记 confirmed not assigned。

## 7. 学情与下一轮

Confirmed trace → deterministic scoring → topic-specific evidence → AI learning summary → next round。学情总结只能引用当前主题已确认 evidence refs；首次正确、提示后/重试、unknown、confirmed skipped 保持语义分离。

## 8. Provider 网关

当前 protocol：`chat`、`responses`、`azure_responses`、`anthropic`、`gemini`、`dashscope`。预设平台及真实/模拟验证边界见 [0.5 状态](product_05_status.md)。密钥不进入备份和仓库。

## 9. 当前边界

- 本机单教师，不是公网多用户权限系统；
- 任意学科结构可生成，但事实正确性仍需教师审核；
- 不上传或执行 AI 生成脚本；
- 不做长篇手写 OCR；
- 不把扫描置信度当学生掌握度；
- 不把协议模拟当真实平台可用性；
- 不把技术测试当学习效果证据。
