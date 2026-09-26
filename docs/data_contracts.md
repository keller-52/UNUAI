# 数据协议与 AI 接口设计

> 版本：1.0 草案。本文定义字段与约束，不是已实现的 API 或正式 JSON Schema。示例见 [完整交互样例](../examples/round_trip.json)。实施时据此编写机器可执行的 Schema。

## 1. 数据对象

| 对象 | 关键字段 | 约束 |
|---|---|---|
| StudentProfile | student_id、class_id、grade、language、accessibility_needs | 编号与姓名映射分开；不发送联系方式给 AI |
| TeachingConfig | unit、goals、prerequisites、excluded_topics、offline_days、page_limits、print_mode | 学习册／记录纸页数分别限制；语言明确 |
| StudentState | state_version、skills、misconceptions、evidence_refs | 每个判断有证据；缺证据时 unknown，不制造精确概率 |
| ScanDraft | scan_id、package_id、package_version、template_id、page_no、fields | 字段含 raw_value、confidence、image_region、review_status |
| ConfirmedTrace | trace_id、trace_version、student_id、package_ref、visits、attempts、feedback、confirmed_by | 只有确认版本可进入正式分析；保留未知，不填猜测值 |
| Evaluation | trace_ref、task_results、support_level、path_discrepancies | 答错与识别失败分开；提示后表现与独立表现分开 |
| AIRequest | request_id、student_state、confirmed_trace、task_context、constraints、content_catalog | task_context 对应原题版本；不得只传答案字母 |
| AIProposal | request_id、diagnosis_proposals、plan、adaptation_notes | 高层任务图，不写实际页码；诊断与内容需审核 |
| CompiledPackage | package_ref、plan_hash、node_page_map、record_template、student_view、teacher_view | 服务端权限隔离；学生响应不包含 teacher_view |
| RoundRecord | round_id、state_ref、trace_ref、package_ref、model_info、prompt_version、approval | 可复现来源、版本、内容与审核关系 |

所有对象携带 `schema_version`。编号、版本、时间戳、内容哈希由程序生成和核验；不能信任 AI 自行创造的学生编号或引用。时间戳使用带时区的 ISO 8601 字符串。

## 2. 记录含义

`visits` 按学生在纸上填写的顺序记录任务编号。`attempts` 每项带 visit_no、task_id、first_answer、hint_level、retry_answer 和 completion_status。首版用无环教学图，重试题使用不同任务编号；若学生实际回跳，照实保留并标注路径异常。

| 字段／值 | 含义 |
|---|---|
| first_answer | 使用提示与自查前记录的答案；真实性受自报限制 |
| hint_level = 0 | 学生明确报告未用提示 |
| hint_level = null | 未记录或无法确定，不等于 0 |
| retry_answer = null | 没有重试答案；结合 completion_status 判断原因 |
| completed | 已有可用完成记录 |
| missing | 按实际路径应做但未提供答案 |
| unreadable | 字段存在但无法可靠读取 |
| not_applicable | 该项对当前任务不适用 |

未访问节点由教学图与 visits 推导，标为 not_visited，不必伪造一条空白作答。记录纸的二维码只用于定位版本；它不构成学生身份认证。

## 3. 教学图约定

首版节点类型为 `choice_question`、`short_question`、`explanation`、`finish`。每个节点都有唯一 id；入口 `entry_node` 必须存在。选择题 options 与 routes 一一对应，包含不确定选项；短答案和讲解节点使用无条件 next。finish 不得有后继。

分支条件只能是学生在纸上能判断的选项／明确自查结果。首版 choice_question 的 routes 默认依据 first_answer，必须把“按首次选项跳转”印在纸上；重试答案只用于回收分析。未来若按重试结果分支，须显式新增规则字段，不能暗中改变语义。任意手写推导理解不属于首版纸上执行能力。完整方案中的答案用于程序评分与教师审核；生成学生视图时删除答案和诊断标签，按教学设计单独放置允许学生自查的内容。

每个题目需记录来源与审核状态；数学题由确定性核验器或教师确认。样例中的手工题目是说明用，不代表已完成题库与答案审核功能。

## 4. AI 调用协议

| 部分 | 内容 |
|---|---|
| 系统任务 | 在给定目标、内容和页数限制内规划可由学生执行的纸质教学路径 |
| 证据输入 | 已确认 trace、原题、评分、提示使用、学生历史；未知值保持未知 |
| 输出要求 | 单一 JSON，返回诊断建议、教学图、调整理由与证据引用；不返回 HTML／脚本 |
| 约束 | 节点数上限、无环、有限提示、语言、知识范围、可选题库 |
| 修复请求 | 原 proposal_id、结构化错误码、出错字段、需要修正的限制 |
| 运行记录 | 模型名称／版本（可取得时）、平台、时间、提示词版本、耗时、调用费用／用量（可取得时） |

教师输入和学生反馈作为数据处理，不能覆盖服务端教学约束。AI 响应先验结构再验内容。误区标签更新也需要证据校验，不能因为输出是合法 JSON 就视为正确。

## 5. 建议 API

| API | 作用 | 关键前置条件 |
|---|---|---|
| POST /students | 新建匿名档案 | 教师权限 |
| POST /teaching-configs | 保存目标与限制 | 范围与资源合法 |
| POST /traces/drafts | 提交本地扫描字段；图片上传为可选独立操作 | 对应包与模板存在 |
| POST /traces/{id}/confirm | 提交人工确认版本 | expected_version 匹配、异常已处理或标未知 |
| POST /evaluations | 依据确认记录评分 | 固定包版本，重复请求幂等 |
| POST /ai-plans | 申请 AI 规划，返回 job_id | 已确认输入、完整题目上下文 |
| GET /jobs/{id} | 查看处理中／成功／失败 | 有权查看所属任务 |
| POST /plans/{id}/validate | 执行结构、内容、路径检查 | 返回所有阻塞错误 |
| POST /plans/{id}/approve | 教师审核通过 | 使用最新已验证版本 |
| GET /packages/{id}/print-data | 下载编译数据，供浏览器生成 PDF | role / view 控制字段，不给学生答案 |
| POST /packages/{id}/issue | 冻结发行版本 | 编译通过、教师批准 |
| GET /rounds/{id}/summary | 获取本轮证据和调整摘要 | 只读访问范围正确 |

编译可作为浏览器内函数 `compile(plan, template, constraints)`；PDF 渲染也在浏览器内进行，不要求单独下载 PDF API。服务端记录编译器与模板版本，便于复现。

## 6. 验证错误与重试

错误对象建议含 code、path、message、recoverable。例如 UNKNOWN_TASK_REF、PACKAGE_VERSION_MISMATCH、UNCONFIRMED_TRACE、INVALID_ROUTE、ANSWER_CHECK_FAILED、PAGE_LIMIT_EXCEEDED、AI_TIMEOUT。

只有 AI 内容可修复错误才提交给 AI 重试；身份／版本错误由程序或教师处理。重试有次数上限，界面展示失败原因；失败方案不能进入 issued。确认、评价和发行接口使用幂等键，更新使用 expected_version，防止重复统计和旧版本覆盖。

## 7. 版本与导出

保留输入、AI 原始响应、校验结果、教师修改、最终图和 PDF 生成信息之间的引用。导出供研究使用时移除身份映射、原图和自由文本中的个人信息。共享仓库只保存虚构示例、协议与脱敏汇总，不提交真实学生档案或密钥。
