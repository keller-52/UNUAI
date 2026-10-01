> 2026-09-28 决定：通用知识单元内容扩展已取消。本文仅保留旧接口的历史说明，不是后续开发计划。两个展示题库位置见 [预留说明](showcase_slots.md)。

> **文档分类：历史文档。** 旧固定 `linear-equations` 单元与单页 OMR 容量接口。 本文保留当时版本的真实设计/验收记录，不代表当前 0.5；当前入口见 [文档索引](README.md) 与 [0.5 状态](product_05_status.md)。

# 知识单元扩展接口 v1

目前只注册 `linear-equations`，不新增知识单元。内容文件为 `demo/units/linear-equations.json`；程序启动时读取该目录的 JSON。`core.load_units()` 是注册入口，`localized_question()` 选择材料语言，`unit_bank()` 获取题库。

| 字段 | 格式与用途 |
|---|---|
| schema_version | 固定字符串 `1.0` |
| id / version | 稳定单元 ID、整数版本；已发行学习包保存内容快照与单元版本 |
| title | `{"en":"…","zh":"…"}` |
| languages | 当前支持 `en`、`zh` |
| skills | 稳定知识点 ID 数组 |
| diagnostic_ids | 本单元诊断题 ID 数组 |
| verification | 校验适配器名称，目前仅 `linear_integer_equation` |
| questions | 题目数组，完整字段见现有单元文件 |

每题包含 `id, skill, level, prompt, options, correct_option, misconception_options, hints, explanation, source`。当前校验器还要求 `equation: {a,b,c}`，含义是 `a*x+b=c`；程序验证整除与答案、选项及错误类型。`translations.zh` 提供中文题面、选项、提示和解析；数学结构和任务 ID 不翻译。

后续添加同类单元可按相同结构提供数据。**跨学科单元必须先注册相应答案校验适配器**，不能把开放题伪装成方程。未知适配器启动时明确拒绝。文件结构接口已预留，不声称任意学科文件现在都能直接运行。当前建档界面仍针对唯一已注册单元，新增单元后还需连接对应诊断表单。

教学配置新增 `unit_id, question_count, language`。一个学生档案绑定一个单元，生成时校验一致性；未来多单元学生应把学生身份与单元学习档案拆开，不能混合两个单元的证据。

当前 OMR-1 支持最多 8 个节点，所以每包开放 2–4 道题，每题（末题除外）可进入一个辅导分支，再加 END。若增加题量或其他节点类型，必须同步扩展记录纸模板、模板版本与扫描器，不能只改题量上限。

默认材料语言为英文，中文可在教学表单选择。界面语言与材料语言独立；切换界面语言不改历史学习包。教学 JSON 和扫描字段采用稳定英文机器键，保留 JSON 调试视图。
