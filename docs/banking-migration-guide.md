# Skill Registry 银行行业迁移与维护指南

> **版本**：v1.0  
> **日期**：2026-07-02  
> **适用**：将 `skill-registry` 双轨能力治理体系迁移至银行/金融行业场景  

---

## 目录

1. [最近两周更新摘要](#一最近两周更新摘要)
2. [银行行业迁移总体思路](#二银行行业迁移总体思路)
3. [关键适配点详解](#三关键适配点详解)
4. [迁移实施路线图](#四迁移实施路线图)
5. [长期维护策略](#五长期维护策略)
6. [附录：检查清单](#六附录检查清单)

---

## 一、最近两周更新摘要

**统计区间**：2026-06-18 至 2026-07-02

> **结论**：最近两周 `master` 分支无新增代码提交。最近一批更新为 **2026-06-16** 的三次提交，内容如下：

| 提交 | 类型 | 说明 |
|------|------|------|
| `a8d290d` | feat | 注册 **stock-analysis skills**（Alpha Knowledge Graph）bundle，新增 4 个股票分析技能 |
| `95bc2f8` | chore | 刷新 `runtime/allowlist.json` — 将新注册技能纳入 Runtime 白名单 |
| `9643b26` | chore | 刷新 `reports/summary.json` — 更新平台评分与健康度徽章数据 |

### 新增资产详情（stock-analysis-skills）

| 技能名 | 用途 | 风险等级 | 状态 |
|--------|------|----------|------|
| `building-portfolio-knowledge-graph` | 构建/刷新投资组合知识图谱（ingest → compress → graph） | L2 | draft |
| `discovering-portfolio-alpha` | 基于知识图谱发现跨标隐藏的 Alpha 信号 | L3 | draft |
| `finding-portfolio-knowledge-gaps` | 识别知识图谱中的覆盖盲区与数据缺口 | L2 | draft |
| `querying-portfolio-brain` | 自然语言问答查询投资组合知识库 | L2 | draft |

**平台健康度快照（更新后）**：
- 总 Skill 数：43（含 3 月平台 meta-skill + 4 月 agent-team 技能 + 新股票技能）
- 总 Tool 数：15
- 平台评分：81/100
- 治理状态：⚠️ WARNING（25 个 stale review 待处理）
- 孤儿 Tool：0
- 状态机检查：PASS

---

## 二、银行行业迁移总体思路

### 2.1 为什么要迁移？

原仓库面向的是**充电桩运维**、**BPMN 流程转换**、**股票分析**等泛互联网/IoT 场景。银行行业的核心差异在于：

| 维度 | 原场景（充电桩/BPMN） | 银行场景 |
|------|----------------------|----------|
| **合规要求** | 一般企业合规 | 银保监会、央行、反洗钱、数据安全法、个人信息保护法 |
| **数据敏感度** | 设备日志、流程描述 | 客户身份信息、交易流水、征信数据、资产负债 |
| **操作风险** | 设备重启/工单派发 | 资金划转、授信审批、合同签署、监管报送 |
| **审计要求** | 日志留存 30-90 天 | 全操作链路留痕、不可篡改、支持监管抽查 |
| **容错要求** | 可接受分钟级中断 | 要求 99.99% 可用性、RTO<15 分钟 |
| **审批层级** | 单级/两级审批 | 多层级（经办→复核→授权→风控→合规） |

### 2.2 迁移原则

1. **框架保留**：Phase 0-6 的七阶段治理体系完全适用，无需推翻。
2. **规则增强**：在银行场景下，风险等级、审批流程、审计要求需大幅加强。
3. **领域替换**：将 `ev-charger-skills`、`business-to-bpmn`、`stock-analysis-skills` 替换为银行业务 bundle。
4. **资产复用**：平台 meta-skill（`capability-planning`、`guiding-skill-authoring` 等）可直接复用，只需调整 references 中的行业示例。

### 2.3 目标架构（迁移后）

```
skill-registry/
├── skill-registry.yaml              # 银行 Skill 中央注册表
├── tool-registry.yaml               # 银行 Tool 中央注册表
│
├── capability-planning/             # Phase 0: 复用，替换银行业务示例
├── guiding-skill-authoring/         # Phase 1S: 复用，更新 constraints 中的银行合规要求
├── guiding-tool-authoring/          # Phase 1T: 复用，更新数据安全约束
├── skill-admission-review/          # Phase 4: 复用，增强冲突检查（银行术语敏感词）
├── tool-admission-review/           # Phase 4T: 复用，增强数据操作风险检查
├── skill-governance-agent/          # Phase 5: 复用，增加审计合规巡检
│
├── bank-credit-skills/              # 信贷业务 Bundle（NEW）
├── bank-risk-skills/                # 风控业务 Bundle（NEW）
├── bank-compliance-skills/          # 合规监管 Bundle（NEW）
├── bank-customer-service/           # 智能客服 Bundle（NEW）
├── bank-reporting-skills/           # 监管报送 Bundle（NEW）
│
└── bank-mcp-tools/                  # 银行 MCP Tool 目录（NEW）
    ├── core-banking-mcp/
    ├── credit-risk-mcp/
    ├── regulatory-mcp/
    └── kyc-aml-mcp/
```

---

## 三、关键适配点详解

### 3.1 风险等级重构（Risk Level Taxonomy）

银行场景下，风险等级必须扩展定义。原 L1-L4 不足以覆盖银行操作的复杂度。

| 等级 | 名称 | 银行场景特征 | 示例 |
|------|------|-------------|------|
| **L0** | 纯查询 | 只读公开数据，无客户信息 | 查询基准利率、汇率 |
| **L1** | 客户信息查询 | 读取客户敏感信息，不修改 | 查询客户账户余额、征信报告 |
| **L2** | 分析与报告 | 生成分析报告，不直接操作资金 | 生成信贷审批意见书、风险评估报告 |
| **L3** | 写操作/通知 | 创建记录、发送通知，不直接动账 | 创建工单、发送短信提醒 |
| **L4** | 资金操作 | 涉及资金变动、合同签署 | 放款、扣款、转账、开卡 |
| **L5** | 监管操作 | 涉及监管报送、数据出境 | 向央行报送征信、反洗钱大额交易报告 |

**适配动作**：
1. 修改 `guiding-skill-authoring/references/platform-constraints.md` 中的风险等级表
2. 修改 `validate_skill.py` 中的 `VALID_RISK_LEVELS` 为 `{"L0", "L1", "L2", "L3", "L4", "L5"}`
3. 修改 `governance_audit.py` 中的 `RISK_SIDE_EFFECTS_MATRIX` 增加 L5 → `external`

### 3.2 审批流程增强（Verify Gate → Multi-Level Approval）

银行场景需要多层级审批，原 L4 的 Verify Gate 必须扩展：

```
[ ] Step N:   验证输入与权限
              - 调用 auth-mcp:verify_user_permission(user_id, operation, scope)
              - 验证是否具备该操作的角色权限
              
[ ] Step N+1: 准备操作参数（脱敏处理）
              - 调用 data-masking-mcp:mask_sensitive_data(raw_data, level="PII")
              
[ ] Step N+2: 提交一级审批（经办）
              - 调用 approval-mcp:request_approval(level=1, operation, params, requester_id)
              - 等待返回：APPROVED / REJECTED / ESCALATE
              
[ ] Step N+3: 提交二级审批（复核/风控）
              - 若一级审批通过且涉及 L4/L5 → 自动触发二级审批
              - 调用 approval-mcp:request_approval(level=2, operation, params, risk_score)
              
[ ] Step N+4: 执行操作
              - 调用核心银行工具执行实际操作
              - 所有参数和操作记录写入审计日志
              
[ ] Step N+5: 验证执行结果
              - 调用 core-banking-mcp:verify_transaction(tx_id)
              - 若失败 → 触发回滚流程，上报异常
              
[ ] Step N+6: 生成审计留痕
              - 调用 audit-mcp:record_operation(trace_id, operation, result, approvers[])
```

**适配动作**：
1. 在 `platform-constraints.md` 中增加多级审批流程模板
2. 在 `validate_skill.py` 的 Dimension 5 (Constraints & Safety) 中增加审批层级检查
3. 新增 `approval-mcp` 到 `REGISTERED_MCP_SERVERS`

### 3.3 数据安全与脱敏（Data Security & Masking）

银行技能必须内置数据安全约束：

| 数据类型 | 处理要求 | 工具 |
|---------|---------|------|
| 客户姓名 | 全量脱敏（张三 → 张*） | `data-masking-mcp:mask_name()` |
| 身份证号 | 部分脱敏（前3后4） | `data-masking-mcp:mask_id_card()` |
| 银行卡号 | 部分脱敏（前6后4） | `data-masking-mcp:mask_bank_card()` |
| 手机号 | 中间4位脱敏 | `data-masking-mcp:mask_phone()` |
| 交易金额 | 范围模糊化（>100万） | `data-masking-mcp:mask_amount()` |
| 征信报告 | 需客户授权 + 用途声明 | `credit-mcp:query_with_consent()` |

**约束规则（写入所有银行 Skill 的 Constraints 节）**：

```markdown
# Constraints

- NEVER output raw PII (personally identifiable information) in any response
- ALWAYS apply data masking before logging or transmitting customer data
- ALWAYS obtain explicit consent before querying credit bureau data
- NEVER store customer data in Skill context across sessions — ephemeral only
- ALWAYS route L4/L5 operations through the multi-level approval gate
- NEVER perform cross-customer data comparison without anonymization
- ALWAYS include `audit_trace_id` in every Tool call for regulatory traceability
- NEVER bypass the Verify Gate for any operation involving funds or customer accounts
```

### 3.4 审计追踪（Audit Trail）

所有银行 Skill 必须满足：

1. **每次 Tool 调用携带 `audit_trace_id`**：贯穿整个请求链路
2. **操作结果不可变记录**：写入不可篡改的审计存储（如 WORM 存储、区块链日志）
3. **支持监管抽查**：技能输出必须包含 `compliance_metadata` 字段
4. **保留期限**：根据监管要求，最低 5 年，部分场景（反洗钱）15 年

**SKILL.md 输出规范增加**：

```yaml
output_schema:
  type: object
  properties:
    result:
      type: object
      description: "业务结果"
    compliance_metadata:
      type: object
      required:
        - audit_trace_id
        - operator_id
        - operation_timestamp
        - data_classification
      properties:
        audit_trace_id:
          type: string
          description: "UUID，贯穿整个请求链路"
        operator_id:
          type: string
          description: "执行操作的用户/系统 ID"
        operation_timestamp:
          type: string
          format: date-time
          description: "ISO 8601 时间戳"
        data_classification:
          type: string
          enum: [public, internal, confidential, secret]
          description: "数据分类等级"
        approvers:
          type: array
          items:
            type: object
            properties:
              level: { type: integer }
              approver_id: { type: string }
              approval_time: { type: string, format: date-time }
```

### 3.5 领域术语与路由防污染

银行术语具有高度专业性，Skill 的 `description` 和 `purpose` 必须精确，避免路由错误：

| 错误示例 | 问题 | 正确写法 |
|---------|------|---------|
| "处理贷款" | 过于宽泛，可能路由到任何信贷相关 Skill | "处理个人住房按揭贷款的首套房利率审批" |
| "查询客户信息" | 无法区分 KYC、征信、账户信息 | "查询客户 KYC 档案中的职业与收入信息" |
| "报送数据" | 可能指内部报表或监管报送 | "向央行征信中心报送个人信贷账户信息" |

**适配动作**：
1. 在 `admission_gate.py` 的"路由治理检查"中增加银行术语模糊词检测
2. 新增 `banking-vocabulary-guide.md` 到 `capability-planning/references/`

### 3.6 监管合规检查（Regulatory Compliance Gate）

建议新增 **Phase 4R（Regulatory Compliance Gate）**，在准入阶段检查：

| 检查项 | 规则 | 严重级别 |
|--------|------|---------|
| R1 数据分类声明 | Skill 必须声明 `data_classification` | CRITICAL |
| R2 客户授权检查 | 涉及客户数据的 Skill 必须有 `consent_required: true` | CRITICAL |
| R3 反洗钱触发词 | 涉及资金移动的 Skill 必须有 AML 检查步骤 | HIGH |
| R4 保留期限声明 | 必须声明数据保留期限（默认 5 年） | WARNING |
| R5 跨境数据检查 | 涉及数据出境的 Skill 必须有 `cross_border_approved` | CRITICAL |
| R6 模型可解释性 | 涉及信贷决策的 Skill 必须输出决策依据 | HIGH |

---

## 四、迁移实施路线图

### Phase 1：基础设施准备（第 1-2 周）

| 任务 | 负责人 | 产出 |
|------|--------|------|
| Fork 仓库并创建 `banking` 分支 | 平台团队 | `banking` 分支 |
| 更新风险等级（L0-L5） | 平台团队 | 修改后的 `platform-constraints.md` + `validate_skill.py` |
| 注册银行 MCP 服务 | 工程团队 | `mcp-tool-catalog.md` 更新 |
| 建立数据脱敏工具 | 工程团队 | `data-masking-mcp` + `audit-mcp` |
| 配置多级审批服务 | 工程团队 | `approval-mcp`（支持 1-3 级审批） |
| 更新 CI 工作流 | DevOps | 新增合规检查 Gate 到 `admission-gate.yml` |

### Phase 2：Meta-Skill 适配（第 3-4 周）

| 任务 | 产出 |
|------|------|
| 更新 `capability-planning` 的银行业务示例 | `classification-guide.md` 新增银行案例 |
| 更新 `guiding-skill-authoring` 的约束模板 | 增加银行数据安全约束模板 |
| 更新 `guiding-tool-authoring` 的风险矩阵 | 增加 L5 + 数据操作风险 |
| 更新 `skill-admission-review` 的冲突检查 | 增加银行术语敏感词库 |
| 更新 `governance_audit.py` | 增加监管合规巡检项 |

### Phase 3：核心业务 Bundle 开发（第 5-12 周）

| 周次 | Bundle | 核心 Skill | 核心 Tool |
|------|--------|-----------|-----------|
| 5-6 | `bank-credit-skills` | 个人信贷申请、企业授信审批 | 征信查询、额度计算、利率定价 |
| 7-8 | `bank-risk-skills` | 信用评分、欺诈检测、预警触发 | 规则引擎调用、模型评分、风险画像 |
| 9-10 | `bank-compliance-skills` | 反洗钱筛查、监管报送、KYC 审核 | 名单筛查、交易监测、报告生成 |
| 11-12 | `bank-customer-service` | 智能问答、投诉处理、产品推荐 | 知识库检索、工单创建、情绪分析 |

### Phase 4：准入与治理（第 13-14 周）

| 任务 | 说明 |
|------|------|
| 运行 `batch_admission.py` | 批量准入检查所有银行 Bundle |
| 运行 `governance_audit.py` | 全库双轨巡检 |
| 生成 `runtime/allowlist.json` | 仅 `approved` 资产进入白名单 |
| 监管合规预检 | 请合规部门预审所有 L4/L5 Skill |
| 灰度发布 | 先上线 L0-L2 技能，逐步开放 L3-L5 |

### Phase 5：持续运维（第 15 周起）

| 频率 | 任务 | 工具 |
|------|------|------|
| 每日 | 运行状态机检查 | `state_guard.py` |
| 每周 | 双轨治理巡检 | `governance_audit.py` |
| 每月 | 合规专项审计 | 新增 `regulatory_audit.py` |
| 每季度 | 风险等级复审 | 人工 + 自动评估 |
| 每年 | 监管报送能力评估 | 外部审计 |

---

## 五、长期维护策略

### 5.1 治理规则演进

| 触发条件 | 治理动作 |
|---------|---------|
| 新监管政策发布 | 更新 `regulatory_audit.py` 检查规则，标记所有受影响 Skill |
| 重大数据泄露事件 | 冻结所有涉及同类数据的 Skill，强制安全审查 |
| 模型漂移检测 | 涉及评分/决策的 Skill 需重新评估和测试 |
| 系统架构变更 | 检查所有依赖该系统的 Tool 的兼容性 |
| 业务线合并/拆分 | 重新评估 `bundle_scope` 边界，调整归属 |

### 5.2 版本管理策略

银行 Skill 采用 **语义化版本 + 监管版本** 双轨管理：

```yaml
version: "2.1.0"          # 语义化版本（功能变更）
regulatory_version: "2026-Q2-CBIRC-001"  # 监管备案版本
compliance_framework:    # 合规框架版本
  - name: "反洗钱法"
    version: "2026-01-01"
  - name: "个人信息保护法"
    version: "2021-11-01"
```

### 5.3 灾备与回滚

- **Skill 回滚**：通过 Registry 状态机 `approved → deprecated` 可在 5 分钟内下线问题 Skill
- **Runtime 白名单**：紧急情况下可直接修改 `allowlist.json` 移除风险资产
- **审批链回滚**：L4/L5 操作必须支持事务回滚，通过 `audit_trace_id` 追踪并撤销

### 5.4 监控指标

| 指标 | 目标 | 告警阈值 |
|------|------|---------|
| 准入通过率 | > 80% | < 70% 触发审查 |
| L4/L5 操作审批平均耗时 | < 5 分钟 | > 10 分钟 |
| 治理巡检 CRITICAL 发现数 | 0 | > 0 立即处理 |
| 审计日志完整率 | 100% | < 100% 立即告警 |
| Skill 路由准确率 | > 95% | < 90% |
| 客户数据泄露事件 | 0 | 任何事件立即冻结 |

---

## 六、附录：检查清单

### 迁移前检查清单

- [ ] 银行 MCP 服务已注册（core-banking, credit-risk, regulatory, kyc-aml, data-masking, audit, approval）
- [ ] 风险等级扩展至 L0-L5
- [ ] 多级审批流程已配置
- [ ] 数据脱敏工具已就位
- [ ] 审计日志存储已配置（不可篡改）
- [ ] CI 流水线已增加合规检查 Gate
- [ ] 合规部门已审阅 `admission-policy.md`
- [ ] 生产环境数据隔离策略已确认
- [ ] 灾备回滚方案已测试
- [ ] 团队已完成银行 Skill 编写培训

### 新增 Bundle 提交检查清单

- [ ] 已运行 `capability-planning` 进行能力规划
- [ ] `validate_skill.py` 评分 ≥ 60（或 ≥ 45 带 review）
- [ ] `validate_tool.py` 评分 ≥ 45
- [ ] 所有 L4/L5 Skill 已通过安全审查
- [ ] 数据分类字段已声明
- [ ] 客户授权字段已声明（如适用）
- [ ] `audit_trace_id` 贯穿所有 Tool 调用
- [ ] 输出包含 `compliance_metadata`
- [ ] `evals/evals.json` 已包含银行场景边界测试用例
- [ ] 已在 `incoming/<bundle>` 分支提交，未污染 master

---

*本文档由平台团队维护，随监管政策和技术演进持续更新。*
