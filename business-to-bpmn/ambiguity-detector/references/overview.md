# Ambiguity Detector · 能力概述

基于意图与实体列表识别歧义与不确定项，并生成面向用户的澄清问题。仅负责识别与产出问题，不替用户做假设、不填默认值。

**职责边界**：仅识别「缺失或矛盾」的信息并输出澄清问题；有歧义时由编排层将问题返回用户并等待回复，不进入规划层。

**输入**：`{ intent: IntentOutput, entities: EntityOutput }` — intent-parser 输出 + entity-extractor 输出。

**输出**：`{ has_ambiguity, ambiguity_points, clarification_questions }` — 歧义标志、歧义点列表、可展示给用户的澄清问题。无歧义时 `has_ambiguity: false`，`ambiguity_points` 与 `clarification_questions` 为空数组。详见 `api-reference.md`。

**典型歧义类型**：scope（范围不清）、trigger（触发条件不明）、role（角色未定义）、constraint（约束缺失）等。
