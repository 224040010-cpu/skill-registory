# 三个配置/日志文件所在位置

本 skill（configuring-pipeline）**拥有**以下三个文件，它们放在**本 skill 目录内**（与 `scripts/`、`references/` 同级），其它流水线脚本通过将 `skills/configuring-pipeline` 加入 `sys.path` 后 `from pipeline_config_loader import load_config` 等方式引用。

| 文件 | 路径（相对项目根） |
|------|-------------------|
| pipeline_config.json | `skills/configuring-pipeline/pipeline_config.json` |
| pipeline_config_loader.py | `skills/configuring-pipeline/pipeline_config_loader.py` |
| pipeline_run_logger.py | `skills/configuring-pipeline/pipeline_run_logger.py` |

运行记录输出文件路径由 `pipeline_config.json` 的 `output.run_log` 决定，默认为：
`{base_dir}/processed_data/pipeline_run_log.jsonl`（相对**项目根**解析后的绝对路径）。

详见项目根目录下的 `pipeline_run_log_说明.md`（若有）。
