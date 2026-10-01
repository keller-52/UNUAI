# 学习包协议

## 可移植文件

格式名称 `paper-ai-learning-package`，格式版本 `1.0`，扩展名建议 `.paper-ai.json`，上传上限 4 MB。

```json
{
  "format": "paper-ai-learning-package",
  "format_version": "1.0",
  "package": {
    "id": "PKG-…",
    "version": 1,
    "sheet_code": "ABCDEF",
    "record_sheets": [],
    "config": {},
    "proposal": {},
    "plan": {},
    "plan_hash": "…",
    "compiler_version": "0.6.0",
    "template_version": "OMR-1",
    "pages": 12,
    "schedule": []
  },
  "checksum": "…"
}
```

上例仅展示字段，不是可导入材料。实际文件由应用导出，必须包含完整题组内容。

`checksum` 使用现有 `content_hash`，对去除 `checksum` 后的整个对象进行规范 JSON 的 SHA-256。它检查文件一致性，不证明材料来自哪一个模型或作者。`plan_hash` 单独覆盖已编译计划。

## 校验与导入语义

`config` 必须是经过 `validate_config` 规范化的自定义主题配置。导入拒绝启用参考题库。题量为 2–3 组、每组 5–10 题；题目、讲解和反馈由现有 `validate_workbook` 检查，重新编译结果必须与文件中的 `plan` 完全一致。

记录纸编号是六位大写十六进制数。主编号与各页编号各不相同；页号连续，每页 1–8 题，按顺序覆盖全部题目且不重复。学习日程必须覆盖相同题号，并位于配置的天数范围内。

导入保留材料 ID、版本和纸张编号，重新生成学生访问令牌，分配本地轮次号，并将状态设为 `draft`、来源设为 `imported`。不导入身份、作答、评价、AI 请求、完整历史或原访问令牌。旧材料摘要保留为内容快照，证据引用不生成本地学习观察。

校验完成后，在全局锁和事务内检查所有碰撞，再插入一份新包。同一学生重复导入相同材料返回现有 ID；不同内容、其他学生或纸张编号碰撞导致失败，不覆盖已有数据。

旧版“导出本轮 JSON”的完整自定义主题包可以直接导入。旧固定题库包、工作区备份、汇总导出、PDF 或仅有 AI 题目响应不支持此入口。

## API

| 请求 | 用途 |
| --- | --- |
| `GET /api/packages/{id}/portable` | 导出一份完整材料 |
| `POST /api/packages/import` | 请求体为 `student_id` 和 `learning_package` |
| `GET /api/backup`、`POST /api/restore` | 带历史的完整工作区迁移 |

导入成功返回 `package_id` 与 `duplicate`。导入包继续使用已有审核、打印、学生视图和记录回收 API。
