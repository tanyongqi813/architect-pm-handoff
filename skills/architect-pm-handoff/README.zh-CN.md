# Architect PM Handoff 中文说明

`architect-pm-handoff` 是一套面向“负责人 AI → 下游执行 Agent”的项目协作协议。它帮助负责人 AI 完成需求分析、架构设计、任务拆分、优先级管理、执行交接和代码评审，同时限制下游 Agent 的上下文范围，减少重复读取文档、源码和历史评审记录所产生的成本。

负责人 AI 可以是 Claude、Codex，或其他被明确授予规划和评审职责的 Agent；下游执行者可以是任意编码 Agent。协作权限由角色决定，而不是由产品或模型名称决定。

## 适用场景

- 在已有代码库中规划下一阶段功能。
- 将较大需求拆成可独立验证的微批任务。
- 由一个 AI 负责架构和验收，多个不同能力的 Agent 负责实现。
- 需要控制执行 Agent 的文件范围、验证范围和上下文消耗。
- 需要保存可追溯的任务状态、评审结论和 Git 提交记录。

该技能不适合让纯执行 Agent 自行规划、调整优先级或批准自己的实现。除非用户另外授权，负责人 AI 也不应越过交接流程直接接管编码。

## 角色划分

### 负责人 AI

负责人 AI 负责：

- 澄清业务结果与非目标；
- 检查现有架构和仓库事实；
- 拆分 Task、设置依赖、优先级与难度；
- 为当前 attempt 生成 Execution Capsule；
- 审查 Implementation Report、代码差异和验证证据；
- 输出评审结论并决定是否进入下一任务；
- 在启用时提交并同步已通过的 Task。

### 下游执行 Agent

执行 Agent 负责：

- 只执行当前 Execution Capsule；
- 只读取胶囊列出的源码锚点；
- 只修改文件白名单中的文件；
- 只运行胶囊允许的定向验证；
- 按固定格式返回精简 Implementation Report；
- 遇到范围扩张、架构冲突、权限不足或事实缺失时停止并报告。

执行 Agent 不负责重新设计架构、扩大任务范围、修改任务优先级或自行批准结果。

## 三层文档模型

### 1. Task Spec：长期规划事实

推荐路径：

```text
docs/tasks/TASK-XXX.md
```

Task Spec 保存相对稳定的内容：

- 业务结果与非目标；
- 架构设计与兼容要求；
- 验收标准；
- 依赖、优先级和难度；
- 主要接口；
- 长期约束。

Task Spec 不再累积执行日志、多轮评审对话和已解决问题。

### 2. Execution Capsule：本轮执行合同

推荐路径：

```text
docs/execution/TASK-XXX/attempt-NN.md
```

一个 Capsule 只服务一次实现或修正 attempt，包含：

- 本轮唯一目标；
- 不允许重新推导的已确认事实；
- 当前仍未解决的 findings；
- 最多五个源码锚点；
- 修改文件白名单及文件数量上限；
- 明确非目标；
- 最多五条定向验证；
- 禁止运行的全量测试、UI 测试、构建或重复验证；
- 已知基线失败；
- 停止条件；
- 固定的 Implementation Report 格式。

新实现建议控制在 1500–2000 中文字，普通修正建议控制在 800–1200 中文字。无法在上限内清晰表达时，优先继续拆分 Task。

完整模板和修正示例见 [`references/executor-handoff.md`](references/executor-handoff.md)。

### 3. Review Record：独立评审历史

推荐路径：

```text
docs/reviews/TASK-XXX/attempt-NN.md
```

Review Record 保存：

- 本轮审查范围；
- 验证证据；
- 稳定 finding ID；
- 架构和范围结论；
- 优先级复核；
- 下一状态与下一胶囊路径。

下一轮修正胶囊只继承仍为 `active` 的 findings，不携带已经解决的历史问题。完整模板见 [`references/review-record.md`](references/review-record.md)。

## 标准工作流

```text
用户需求
   ↓
负责人 AI 检查仓库与架构事实
   ↓
创建或更新 Task Spec 与 TASK_LIST
   ↓
生成当前 attempt 的 Execution Capsule
   ↓
下游 Agent 实现、定向验证、提交精简报告
   ↓
负责人 AI 评审并写入 Review Record
   ├─ PASSED / PASSED_WITH_NOTES → 完成当前 Task，选择下一 READY Task
   ├─ CHANGES_REQUESTED → 仅针对 active findings 生成 delta Capsule
   └─ BLOCKED → 等待产品、架构或权限决策，不派发
```

只有存在一个完整、明确且可执行的 Capsule 时，负责人 AI 才输出：

```markdown
### 发给执行代理的下一步指令（难度：Medium）
> 执行 @docs/execution/TASK-XXX/attempt-NN.md。只读取胶囊列出的源码锚点，只修改白名单文件，只运行定向验证，并按胶囊格式返回精简 Implementation Report。
```

没有该标题即代表 `no dispatch`，自动派发系统不应启动下游 Agent。

## 微批与难度规则

每个 Task 默认只涉及 1–3 个主要实现文件。超过三个时原则上继续拆分；只有不可分割事务、接口迁移或原子数据流可以例外，并需要在 Task Spec 中说明原因。

优先级：

- `P0`：生产事故、安全漏洞、数据丢失或发布阻断；
- `P1`：当前里程碑关键路径或重要近期风险；
- `P2`：普通计划任务，默认等级；
- `P3`：可选优化或延期改进。

难度：

- `Low`：明确、低风险、已有模式可遵循；
- `Medium`：局部设计或诊断，存在适度交互；
- `High`：跨模块状态、迁移、安全、并发、性能或需要较强判断。

难度用于选择适合的执行 Agent，不能由优先级直接推导。

## CHANGES_REQUESTED 的 delta handoff

复审不重新派发整个原任务。新的修正 Capsule 应当：

- 只包含最新 Review Record 中仍未解决的 finding；
- 明确未被 finding 指向的既有实现保持不动；
- 缩小源码锚点、文件白名单和验证范围；
- 不重复已经通过的验证；
- 不复制原任务叙述或已解决的评审历史。

## 旧项目兼容

只有 `docs/tasks/TASK-XXX.md` 的旧项目仍可继续使用。系统采用惰性迁移：

1. 在下一次派发或修正前检查当前仓库事实；
2. 能确认目标、锚点、白名单、验证和基线时生成 `attempt-01`；
3. 无法确认的字段标记为 `待确认`，不伪造结论，也不输出派发信号；
4. 旧 Task Spec 中已有评审历史保留原样，新评审开始写入独立 Review Record。

旧版 Task Spec 指针仍可作为兼容入口，但不具备 Execution Capsule 的上下文效率保证。

## 渠道适配器

核心协议不关心执行 Agent 的厂商或调用方式。认证、CLI 参数、模型选择、超时、恢复和权限由独立 adapter 处理。

当前包含 Cursor CLI adapter：

```text
references/adapters/cursor-cli.md
```

其他执行渠道可以增加各自 adapter，但不得把供应商名称或模型特性写进共享 Task Spec、Capsule 或 Review Record。

## 已通过任务的 Git 同步

自动提交和推送默认关闭。公开配置位于 `config.example.toml`，个人配置应写入不进入版本控制的 `config.local.toml`。

启用后，只有 `[PASSED]` 或 `[PASSED_WITH_NOTES]` 的 Task 可以自动提交。提交范围限定为当前 Task 的实现、测试、必要生成文件、Task Spec、当前 Capsule、Review Record、任务列表，以及该 Task 引起的架构文档变更。

提交信息记录 Task ID、评审结论、优先级、难度、验证结果和文件列表。系统不会自动创建 upstream、强推、改写历史、切换分支、合并或创建 Pull Request。

## 推荐仓库结构

```text
docs/
├── ARCHITECTURE.md
├── TASK_LIST.md
├── decisions/
├── tasks/
│   └── TASK-016.md
├── execution/
│   └── TASK-016/
│       ├── attempt-01.md
│       └── attempt-02.md
└── reviews/
    └── TASK-016/
        ├── attempt-01.md
        └── attempt-02.md
```

## 上下文效率目标

正确生成的 Execution Capsule 应满足：

- 新执行者阅读一次胶囊即可开始；
- 不需要全文读取前置 Task Spec 或历史评审；
- 上下文压缩后只需重读胶囊和当前修改文件；
- 负责人可以直接看到文件范围和验证上限；
- Review Record 持续增长不会增加后续执行提示词长度。
