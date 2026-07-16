# OCR Benchmark 通用工作流

## 目录

- [首次确认模板](#首次确认模板)
- [配置字段](#配置字段)
- [内置脚本起步](#内置脚本起步)
- [推理命令骨架](#推理命令骨架)
- [裁判命令骨架](#裁判命令骨架)
- [计分命令骨架](#计分命令骨架)
- [测试集更换规则](#测试集更换规则)
- [错误处理](#错误处理)
- [报告与排行输出](#报告与排行输出)

## 首次确认模板

首次使用时先问：

> 请告诉我本次正式裁判使用的模型 `model id` 和 API `URL`。如果测试集、报告目录或排行目录不是仓库默认值，也请一并给出。

当前会话已经明确提供 model id 和 URL 时，只复述确认，不重复询问。

## 配置字段

每次运行建立独立配置，至少记录：

| 字段 | 含义 |
| --- | --- |
| `test_data_path` | 本次测试数据入口，可为 JSONL、JSON、目录或仓库支持的其他格式 |
| `manifest_path` | 可选；完整计分清单 |
| `expected_records` | 预期样本数 |
| `dataset_id` | 数据集或冻结版本标识 |
| `model_id` | 参赛模型 API ID |
| `model_api_url` | 参赛模型 API URL |
| `model_api_key_env` | 参赛模型 key 的环境变量名 |
| `model_source_label` | 报告使用的 API 来源名称 |
| `thinking_mode` | thinking、non-thinking 或 API 默认 |
| `prompt_group` | 提示词分组名称 |
| `run_output_dir` | 预测、错误和裁判 JSONL 目录 |
| `report_output_dir` | Markdown 报告目录，可单独设置 |
| `ranking_output_dir` | 排行文件目录，可单独设置 |
| `judge_model_id` | 用户确认的裁判 model id |
| `judge_api_url` | 用户确认的裁判 API URL |
| `judge_api_key_env` | 裁判 key 的环境变量名 |
| `judge_prompt_version` | 当前 benchmark 定义的裁判提示词版本 |
| `judge_reasoning_mode` | 正式裁判 reasoning 模式 |

不要把任何测试集路径、样本数、数据集 ID、裁判模型或 API URL 固定在 skill 中。

## 内置脚本起步

仓库没有现成工具时，可使用 skill 自带脚本：

```powershell
python -B <skill-dir>/scripts/init_testset.py --root <testset-root>
python -B <skill-dir>/scripts/init_testset.py --root <testset-root> --layout extended --apply
python -B <skill-dir>/scripts/audit_testset.py --root <testset-root>
python -B <skill-dir>/scripts/validate_run.py --test-data <test-jsonl> --predictions <predictions-jsonl>
```

第一条只显示创建计划；确认后再加 `--apply`。完整参数以各脚本 `--help` 为准。

## 推理命令骨架

先查看仓库脚本的 `--help`，再把占位符映射到真实参数。若仓库提供 OpenAI-compatible 评测脚本，可按以下形式组织：

```powershell
python -B <inference-script> `
  --data-path <test-data-path> `
  --url $env:OCR_MODEL_URL `
  --model <model-id> `
  --api-key-env OCR_MODEL_API_KEY `
  --output <run-output-dir>/<run>_predictions.jsonl `
  --summary <run-output-dir>/<run>_predictions_summary.json `
  --errors <run-output-dir>/<run>_predictions_errors.jsonl `
  --workers <workers>
```

提示词、`max_tokens`、temperature、top-p、thinking 和图片预处理参数以本次运行配置为准，不在 skill 中设置固定值。

支持断点的脚本通常会读取已有 output JSONL。错误文件可能多次记录同一图片，因此最终完整率应按唯一预测图片与本次测试集的差集计算。

## 裁判命令骨架

```powershell
python -B <judge-script> `
  --input <predictions.jsonl> `
  --output <run-output-dir>/<run>_judge.jsonl `
  --summary <run-output-dir>/<run>_judge_summary.json `
  --errors <run-output-dir>/<run>_judge_errors.jsonl `
  --url $env:OCR_JUDGE_URL `
  --model <judge-model-id> `
  --prompt-version <judge-prompt-version> `
  --api-key-env OCR_JUDGE_API_KEY `
  --workers <2-5>
```

reasoning、响应格式和最大输出长度必须服从当前 benchmark 规则。正式裁判与争议复核使用不同文件。

使用 skill 默认裁判提示词时，把 `__REFERENCE__` 和 `__PREDICTION__` 分别替换为真值与预测；不要对整份模板直接调用会解析 JSON 大括号的字符串格式化方法。

## 计分命令骨架

```powershell
python -B <score-script> `
  --manifest <optional-manifest> `
  --predictions <predictions.jsonl> `
  --judge <judge.jsonl> `
  --summary <run-output-dir>/<run>_score_summary.json `
  --samples-output <run-output-dir>/<run>_samples.jsonl `
  --report <report-output-dir>/<report-name>.md `
  --run-name <run>
```

如果计分脚本不支持某个参数，按其 `--help` 调整，不要为了套模板改坏现有计分逻辑。

## 测试集更换规则

更换测试集时重新确认测试入口、manifest、样本数、图片解析根目录、标签字段、分类字段、难度字段和数据集 ID。旧预测只有在样本 ID、图片路径和图片哈希都匹配时才能复用；文件名相同不足以证明可复用。

训练集和测试集必须隔离。若仓库提供图片哈希审计，正式运行前检查训练/测试重叠。

## 错误处理

- 429 或短暂 502/503/504：保留输出、降低并发、断点续跑，再隔离持续失败样本。
- 持续 504：记录样本 ID、图像尺寸、已试参数和最终缺失状态。504 只能证明网关未及时得到响应。
- `model_not_found`：停止并让用户确认 model id，或在授权范围内查询模型列表。
- HTTP 402 或额度耗尽：停止批次并保留有效记录；更换裁判时创建全新的正式裁判文件。
- 裁判 JSON 无效：在同一裁判组重试，不用其他 reasoning 模式替换单条结果。

## 报告与排行输出

`report_output_dir` 与 `ranking_output_dir` 相互独立：

- 只要求报告时，不修改排行目录。
- 只要求排行时，先确认报告链接策略；没有报告时允许使用无链接行或用户指定链接。
- 两者都要求时，先生成并核验报告，再更新排行。
- 输出到现有目录前先备份将被覆盖的文件。

报告建议顺序：

1. `先说结论`
2. `优势：它真正擅长什么`
3. `不足：它会怎样失败`
4. 参数、thinking、API 来源与测试集
5. 详细结果

来源名称使用用户确认的公开标签。不得发布 API key、私有 API URL 或内部路由信息。

仓库没有既定模板时，从 skill 的 `assets/templates/report.md` 和 `assets/templates/ranking.md` 复制到各自输出目录后再填写。不要让报告输出目录隐式决定排行目录，反之亦然。
