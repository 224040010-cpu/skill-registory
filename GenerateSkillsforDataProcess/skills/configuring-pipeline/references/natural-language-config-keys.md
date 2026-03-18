# 支持通过自然语言修改的配置键

用户说「把数据目录改成 data2」「向量库默认改成重建」等时，Agent 将意图映射为下表中的键路径，并调用本 skill 的 **scripts/apply_config_change.py** 或直接编辑 pipeline_config.json 完成修改。

| 用户表达示例 | 键路径 | 值类型 | 说明 |
|--------------|--------|--------|------|
| 用 xxx 环境 / conda 环境改成 xxx / 运行前选 xxx 环境 | conda_env | string | 运行 phase 脚本时使用的 conda 环境名；空表示当前环境 |
| 数据目录改成 xxx / base_dir 改成 xxx | base_dir | string | 数据根目录名，如 "data", "data2" |
| 向量库/ChromaDB 默认重建 | vectorizing.chromadb.rebuild | bool | true=每次重建；false=增量(默认) |
| HippoRAG 默认重建 | vectorizing.hipporag.rebuild | bool | true=强制重建；false=增量(默认) |
| Unstructured API 地址 | unstructured.api_url | string | 默认 https://api.unstructuredapp.io/general/v0/general |

**布尔值**：脚本或编辑时用 `true` / `false`；自然语言中「重建」「增量」「不重建」等由 Agent 映射为 true/false。

**敏感项**：api_key 类建议用 "${env:VAR}"，由用户自行在环境中设置，不通过自然语言写入明文。
