# Skill Registry 与 Agent Workflow Factory 仓库职责边界

## 1. 文档目的

本文档定义 `skill-registory` 与 `agent-workflow-factory` 的职责、数据交换、变更发布和故障隔离规则。它用于回答：

- 哪类资产应该放在哪个仓库；
- 哪个仓库拥有最终解释权；
- 两个仓库通过什么固定契约协作；
- 哪些变更需要双仓同步，哪些不需要；
- Registry 或 Factory 故障时，运行中的工作流应如何处理。

核心原则是：**Registry 决定“什么能力有资格被使用”，Factory 决定“这些能力如何被组装和执行”。**

## 2. 总体架构

```text
┌────────────────────────────────────────────┐
│ skill-registory：能力治理控制平面          │
│                                            │
│ Capability Planning                        │
│ → Skill / Tool 规范                        │
│ → Authoring Gate / Admission Gate          │
│ → 生命周期、风险、Owner、评测和审计         │
│ → 发布 Capability Catalog                  │
└──────────────────────┬─────────────────────┘
                       │ 固定 Catalog 快照
                       ▼
┌────────────────────────────────────────────┐
│ agent-workflow-factory：流程编译与执行平面 │
│                                            │
│ 业务语言 → BPMN → Workflow IR              │
│ → Graph / Loop → Agent Profile             │
│ → Registry Lock → 签名软件包               │
│ → Runtime / DeepSeek Harness               │
│ → 事件轨迹、暂停、恢复与重放                │
└──────────────────────┬─────────────────────┘
                       │ 运行证据和治理建议
                       ▼
               Registry 人工评审入口
```

## 3. `skill-registory` 负责什么

`skill-registory` 是权威能力控制平面，拥有以下内容的最终解释权：

### 3.1 能力建模

- 判断需求应建模为 Skill、Tool，还是父 Skill 内部步骤；
- 定义 Skill 的触发边界、输入输出、步骤、异常和完成证据；
- 定义 Tool 的请求/响应 Schema、Endpoint、幂等性和副作用；
- 维护能力命名、拆分、合并和升降级规则。

### 3.2 生命周期与风险治理

- 维护 `skill-registry.yaml` 与 `tool-registry.yaml`；
- 管理 `draft`、`submitted`、`approved`、`restricted`、`deprecated`、`retired` 等状态；
- 维护 Owner、版本、风险等级、评测和安全审查结果；
- 检查 Skill/Tool 依赖、孤儿 Tool、过期审查和高风险调用链；
- 执行 Authoring Gate、Admission Gate、State Guard 和周期治理巡检。

### 3.3 Catalog 发布

- 生成版本化的 `catalog/catalog.snapshot.json`；
- 只发布 `approved` 和 `restricted` 资产；
- 为每个发布资产提供版本、状态、风险和 SHA-256 摘要；
- 隔离 `draft`、`submitted`、`needs_revision`、`deprecated` 和 `retired` 资产。

### 3.4 共享总定义

- 保存 `contracts/system-definition.json` 的权威副本；
- 决定何时提升总定义版本；
- 维护 `contracts/system-definition.sha256`；
- 协调 Factory 中镜像副本的同步。

## 4. `skill-registory` 不负责什么

以下内容不得继续堆入 Registry：

- 面向具体业务请求的 BPMN 实例生成；
- BPMN 解析、Workflow IR 和 Graph 路由实现；
- Loop 的运行时轮次、停止条件执行和调度；
- 针对某个流程生成的 Agent Profile；
- DeepSeek Harness 或其他模型 Harness 适配器；
- 运行会话、检查点、事件轨迹、暂停、恢复和重放；
- 构建私钥、离线根私钥、模型 API Key 和生产运行凭据。

Registry 可以定义这些能力需要满足的治理契约，但不拥有其运行实现。

## 5. `agent-workflow-factory` 负责什么

`agent-workflow-factory` 是流程编译与执行平面，负责：

### 5.1 业务语言和 BPMN

- 接收业务人员的自然语言描述；
- 生成并校验 BPMN；
- 返回业务视角流程图；
- 将 BPMN 解析为标准 Workflow IR。

### 5.2 Graph Engineering 与 Loop Engineering

- 将 Workflow IR 编译为可路由 Graph；
- 生成分支、并行、回退、循环和终止条件；
- 把 BPMN Lane、Task 和责任映射为 Agent Profile；
- 对运行预算、最大轮次和升级条件实施约束。

### 5.3 能力解析与确定性构建

- 消费一个明确版本的 Catalog 快照；
- 只解析 Catalog 中存在且状态允许的 Skill/Tool；
- 生成 `registry.lock.json`，固定 Catalog、资产版本和摘要；
- 把 BPMN、IR、Graph、Agent、Policy、Loop 和 Lock 打包为完整工作流软件包。

### 5.4 信任、运行与证据

- 签署 Registry Lock 和完整软件包 Manifest；
- 在执行前验证根信任、Binding、Registry Lock 和软件包完整性；
- 适配 DeepSeek Harness 等真实 Agent Runtime；
- 保存事件轨迹、预算用量和检查点；
- 支持暂停、恢复、失败分支和确定性重放。

## 6. `agent-workflow-factory` 不负责什么

Factory 不得：

- 直接修改 Skill/Tool 的权威生命周期状态；
- 在运行期间从 Registry 主分支发现或升级资产；
- 绕过 Catalog 使用 `draft`、`deprecated` 或 `retired` 资产；
- 把运行成功自动等同于 Registry 准入通过；
- 在本仓库之外重新定义一套不兼容的 Skill/Tool 风险政策；
- 把运行时反馈直接写入权威 Registry，而不经过治理评审。

## 7. 职责矩阵

| 能力或资产 | Registry | Factory |
|---|---|---|
| Skill/Tool 分类规则 | 负责 | 遵守 |
| Skill/Tool 源规范 | 负责 | 消费 |
| Registry 生命周期和风险策略 | 负责 | 强制使用结果 |
| Capability Catalog | 生成和发布 | 固定和消费 |
| 共享总定义 | 保存权威副本 | 保存字节一致镜像 |
| 自然语言需求解释 | 提供相关能力规范 | 负责具体实例 |
| BPMN 生成和校验 | 提供可用 Skill/Tool | 负责 |
| Workflow IR、Graph、Loop | 不负责 | 负责 |
| Agent Profile | 不负责 | 负责 |
| Registry Lock | 提供 Catalog 输入 | 生成和签署 |
| 完整软件包 Manifest | 不负责 | 生成、签署和验证 |
| Harness/Runtime | 不负责 | 负责 |
| 运行事件与检查点 | 不负责 | 负责 |
| 治理状态变更 | 评审并执行 | 只能提出建议 |

## 8. 双仓集成契约

两个仓库必须遵守以下顺序：

1. Registry 完成 Skill/Tool 编写校验和准入评审。
2. Registry 根据生命周期状态发布固定 Catalog 快照。
3. Factory 将该快照作为一次构建的显式输入，而不是读取不断变化的主分支。
4. Factory 解析所需能力并生成 `registry.lock.json`。
5. Lock 必须记录 Catalog 摘要、总定义版本、资产名称、版本和摘要。
6. Factory 生成 BPMN、Workflow IR、Graph、Loop 和 Agent Profile。
7. Factory 签署 Registry Lock 和完整软件包 Manifest。
8. Runtime 在执行模型或 Tool 前验证信任链和软件包文件集合。
9. Runtime 产生的证据可以形成治理建议，但必须经过 Registry 的人工或政策评审后才能改变资产状态。

## 9. 共享总定义同步规则

`contracts/system-definition.json` 在逻辑上只有一份定义，在物理上分别保存在两个仓库。当前权威仓库是 `skill-registory`。

总定义发生变化时必须：

1. 在 Registry 中修改权威文件；
2. 提升 `definition_version`；
3. 刷新 `contracts/system-definition.sha256`；
4. 将文件逐字节同步到 Factory；
5. 在两个仓库中分别运行校验；
6. 重新发布 Catalog，并按需重新编译受影响的软件包。

双仓同时位于本机时，可以执行：

```bash
python scripts/verify_system_definition.py \
  --peer ../agent-workflow-factory/contracts/system-definition.json
```

普通 Skill/Tool 的新增、版本升级或状态变化不应修改总定义，只需更新 Registry、重新发布 Catalog，并由需要升级的工作流显式重新锁定。

## 10. 变更归属判断

| 变更示例 | 应修改的仓库 | 是否需要双仓同步 |
|---|---|---|
| 新增一个业务 Skill | Registry | 否，发布新 Catalog 即可 |
| 新增一个 MCP Tool 契约 | Registry | 否，发布新 Catalog 即可 |
| Tool 从 `draft` 升为 `approved` | Registry | 否，Factory 选择是否重新锁定 |
| 修改 Skill/Tool 资产类型的全局定义 | Registry + Factory | 是，提升总定义版本 |
| 优化自然语言转 BPMN 算法 | Factory | 否 |
| 增加新的 Graph 路由节点类型 | Factory；若改变跨仓契约则双仓 | 视契约影响而定 |
| 增加 KMS/HSM Signing Provider | Factory | 否 |
| 根据运行证据吊销高风险 Tool | Registry | Factory 后续构建使用新 Catalog |

## 11. 故障与隔离原则

### Registry 暂时不可用

- 已签署并固定 Catalog/Lock 的工作流可以继续运行；
- 不允许临时回退到读取 Registry 主分支；
- 新工作流构建必须等待可信 Catalog 输入，或使用经过批准的本地固定快照。

### Catalog 发生变化

- 已构建软件包不得自动漂移；
- 需要升级的工作流必须重新解析、重新锁定、重新签署并重新验证；
- `deprecated` 或 `retired` 状态不应静默修改历史软件包，但可由运行政策阻止其继续部署。

### Factory 或 Runtime 发现异常

- 摘要、签名、文件集合或根信任验证失败时必须在模型调用前终止；
- Tool 输出与模型声明不一致时，以可信 Tool 证据为准并拒绝错误事实；
- 运行异常只能产生证据和治理建议，不能自动篡改 Registry 状态。

## 12. 边界验收清单

发布前应确认：

- [ ] Skill/Tool 权威定义只在 Registry 中维护；
- [ ] Catalog 只包含 `approved` 和 `restricted` 资产；
- [ ] Factory 使用固定 Catalog，而不是运行时访问主分支；
- [ ] `registry.lock.json` 固定了版本和摘要；
- [ ] 软件包执行前完成签名与完整性验证；
- [ ] 生产私钥和 API Key 没有进入 Registry；
- [ ] 运行证据通过治理流程反馈，没有直接修改生命周期；
- [ ] 共享总定义在两个仓库逐字节一致。

---

本文档更新于 2026-08-29，适用于 `skill-registory` 当前控制平面和 `agent-workflow-factory` v0.9 执行平面。
