# PAPER AI 0.5 当前数据协议

> **文档分类：当前文档。** 更新：2026-09-28。本文是实现语义说明，不是完整 JSON Schema；实际字段与验证以 `demo/server.py`、`demo/workbook.py`、`demo/providers.py` 为准。早期 [round_trip.json](../examples/round_trip.json) 仅为历史示例。

## 1. 主要对象

| 对象 | 当前关键内容 |
|---|---|
| Student | 匿名 student_id、年级/班级、固定单元兼容信息 |
| TeachingConfig | language、question_count、batch_size、offline_days、custom_topic/topic_id、背景与目标等 |
| StudentState | 当前主题 evidence、状态说明；无证据时保持 unknown |
| AI Workbook Proposal | title、reason、learning_summary、evidence_refs、lesson、questions、batch_feedback |
| Package | proposal + compiled plan + config + audit + version + record_sheets |
| Trace | package/version、rows、source、confirmed、skipped_batches |
| Evaluation | 每题首次/重试/提示、completion、统计、routing_mode/skipped_batches |
| ProviderConfig | provider、protocol、base_url、model、json_mode、api_key（私有） |

## 2. 当前 AI Workbook Proposal

自定义主题主结构：

```json
{
  "title": "...",
  "reason": "...",
  "learning_summary": "...",
  "evidence_refs": [],
  "lesson": [{"heading":"...","text":"...","example":"..."}],
  "questions": [{"id":"Q1","prompt":"...","skill":"...","options":[],"correct_option":"B","hints":["...","..."],"explanation":"...","design_reason":"...","origin":"ai_generated"}],
  "batch_feedback": [{"batch":1,"title":"...","focus":"...","guidance":"Markdown..."}]
}
```

题数必须等于 config 指定值，Q ID 连续，四个选项 A–D 唯一，correct_option 合法，每题两级提示。

## 3. 自由 guidance 语义

`batch_feedback[].guidance` 是当前 0.5 主路由形式。程序允许 AI 自由决定教学政策，不强制 targeted condition 顺序、score fallback 穷尽、固定难度梯度、首组必须两个目标、前向跳转、全组可达或无回访。

程序只检查能确定的显式引用，例如 guidance 中出现的 Q 编号或题组编号不得超出当前包。教师负责判断条件是否清楚、是否会死循环、何时结束。

旧 `rules[]` 仍可存在作为兼容结构，但不是当前自定义主题的推荐格式。

## 4. Compiled Plan

自由指导包核心字段：

```text
layout = batch-v1
routing_version = free-guidance-1
batch_size
batch_feedback
lesson
nodes = Q1..Qn + END
verification = structure_only_teacher_review_required
```

`nodes[].routes` 对自由指导包只是连续问题的兼容数据，不代表后台自动执行 AI 的自然语言教学决策。

## 5. Trace 行语义

每题记录：

```text
task_id
first_answer = A/B/C/D/null
hint_level = 0/1/2/null
retry_answer = A/B/C/D/null
```

关键区分：

- `null` 不是自动错误；
- first answer 永远不被 retry 覆盖；
- hint 0 表示明确未使用；null 表示未知；
- `skipped_batches` 只保存教师明确确认的“未分配题组”。

自由 guidance 模式下，空白题先作为 `unanswered_or_skipped`。若某组存在答案、提示或重试，就不能同时列入 `skipped_batches`。

## 6. Evaluation

确定性程序可以计算 first_correct/first_total、retry_correct、hint=0 的 independent 统计、每题 completion、warnings 和 confirmed skipped groups。

自由 guidance 模式使用 `routing_mode = teacher_review`，不会声称自动恢复自然语言路线。旧结构化包仍可保留 prescribed path 的兼容结果。

## 7. ProviderConfig

当前 protocol：`chat`、`responses`、`azure_responses`、`anthropic`、`gemini`、`dashscope`。每种协议在 `providers.py` 中负责不同 URL、鉴权、system message、JSON 模式与响应抽取。

密钥不返回公共状态、不写入教学数据库/备份、不提交 Git；更换服务地址时不自动沿用旧密钥。

## 8. 版本、冻结与恢复

Package 在教师批准后冻结。下一轮是新 package，不覆盖旧包。Trace 修订保存历史；重复确认不得重复累计。备份恢复校验引用与冲突，不包含 API key。

数据合同的原则是：**机器只声明自己能确定的事实，自由教学策略和无法识别的纸面含义留给教师确认。**
