# 开发场景 OCR Benchmark v4 规划

> 本文是历史评测规则。v4 是 Benchmark 版本，文中的 v6 是模型版本；当前规则见 [benchmark_guide_v5.md](benchmark_guide_v5.md)。

更新时间：2026-06-10

## 目标

Benchmark v4 以 benchmark v3 为基础继续完善，保留 v3 已验证的 LLM 六维裁判经验，但重做最终积分公式。v4 的核心改进是把测试集从 50 题扩展到 100 题，并按活动规则覆盖更多开发场景，让结果更能反映模型在真实开发 OCR 中的稳定性。

v4 重点补齐 v3 的不足：

- v3 测试集偏向 IDE 截图，终端、配置、diff、文档代码块、错误日志和困难样本覆盖不足。
- v3 只有整体分，缺少按任务类型拆解的弱项定位。
- v3 对“平均表现”刻画较好，但对小类崩坏、长输出发散、UI 噪声、表格和 patch 类样本的专项压力不足。

v4 的定位：

- `benchmark v3`：继续作为当前主线历史排名口径。
- `benchmark v4`：作为活动规则 100 题扩展集和下一阶段主评测候选。
- 两者结果不得混排；报告中必须明确数据集、总题数、裁判版本和积分版本。

## 数据集

当前活动测试集已经切换为 UI 渲染分类版：

```text
测试集/
```

推荐评测入口：

```text
test.jsonl
```

辅助入口：

| 路径 | 用途 |
| --- | --- |
| `测试集/` | 当前活动测试集，100 对图片和 `.txt`，按分类组织。 |
| `test.jsonl` | 当前活动评测入口，100 条。 |
| `test.json` | 同内容 JSON 版。 |
| `benchmark_v4_workspace/final_ui/test_v4_ui.json` | JSON 版评测入口。 |
| `benchmark_v4_workspace/final_ui/测试集/` | 完整 100 对图片和 `.txt`。 |
| `benchmark_v4_workspace/final_ui/测试集_按分类/` | 按活动规则分类后的 100 对样本。 |
| `benchmark_v4_workspace/final_ui/新增/` | 本轮新增 50 对 UI 渲染样本。 |
| `benchmark_v4_workspace/final_ui/sources.jsonl` | 新增样本来源、类别和哈希记录。 |
| `benchmark_v4_workspace/final_ui/by_category_manifest.jsonl` | 100 题分类映射清单。 |
| `benchmark_v4_workspace/final_ui/人工校对报告.md` | 新增 50 题人工核验记录。 |
| `benchmark_v4_workspace/final_ui/quality_audit.tsv` | 机械质检结果。 |

历史目录只作归档：

- `backups/testset_v3_archived_20260610/`：旧 50 题测试集和旧 `test.json` / `test.jsonl`。
- `benchmark_v4_workspace/draft_online/`：早期 online 草稿，包含较多合成或非最终样本。
- `benchmark_v4_workspace/intermediate_real/`：真实网页采集中间版，包含 raw/diff 默认文本页等非最终样本。

## 分类配额

v4 固定为 100 题，分类如下：

| 类别 | 数量 | 评测关注点 |
| --- | ---: | --- |
| IDE 代码编辑器截图 | 20 | 代码正文、文件名、标签页、多区域 UI、暗色/亮色主题。 |
| 终端 / Shell / PowerShell | 15 | 命令、参数、路径、状态输出、表格型终端文本。 |
| 报错日志 / Traceback | 15 | 堆栈顺序、错误类型、文件路径、行号、caret 指示。 |
| 配置文件 / YAML / JSON / TOML / INI | 15 | 缩进、冒号、引号、数组、嵌套层级、布尔/数字。 |
| Git diff / patch / PR 页面 | 10 | `+/-` 前缀、hunk header、文件路径、上下文顺序。 |
| 网页代码块 / 文档代码块 | 10 | 渲染代码块、代码围栏、复制区域、文档正文干扰。 |
| 表格化代码信息 / 参数表 / API 文档 | 5 | 表头、列对齐、参数名、类型、必填/可选信息。 |
| 模糊、压缩、拍屏、暗色主题、小字号等困难样本 | 10 | 抗噪声、低对比、小字号、密集结构、复杂排版。 |

## 数据验收

v4 数据集进入正式评测前必须满足：

- 图片数量 100，文本数量 100，JSONL 记录 100。
- 每张图片有且只有一个同名 `.txt`。
- 新增样本与 `train/`、`评估集_20260601/`、`测试集/` 的 stem 和图片哈希均无重叠。
- 新增样本必须人工逐张核验图片与 `.txt` 一致；OCR/VLM 工具只能做辅助，不能替代最终判断。
- `.txt` 只包含图片中清晰可见文字，不包含隐藏 DOM、横向不可见内容、解释、总结或补全。
- `dataset/audit_dataset_quality.py` 机械质检 findings 为 0。

当前已完成的验收记录：

- `benchmark_v4_workspace/final_ui/测试集/`：100 图片 + 100 txt。
- `benchmark_v4_workspace/final_ui/test_v4_ui.jsonl`：100 条。
- 当前根目录 `测试集/`：100 图片 + 100 txt。
- 当前根目录 `test.jsonl`：100 条。
- `benchmark_v4_workspace/final_ui/quality_audit.tsv`：当前 findings 为 0。
- `benchmark_v4_workspace/final_ui/人工校对报告.md`：新增 50 题人工核验通过。
- 旧 50 题已归档到 `backups/testset_v3_archived_20260610/`；当前根目录测试集已切换为 v4 100 题分类版。

## 裁判口径

v4 继续使用 `dev_ocr_judge_v4` 六维 LLM 裁判，不重新设计裁判 prompt。这样可以最大限度复用 v3 的人工校准经验，并保持结果解释一致。

六个原始维度保持不变：

| 字段 | 满分 | 含义 |
| --- | ---: | --- |
| `content_coverage_0_10` | 10 | 主要内容覆盖。 |
| `symbol_accuracy_0_10` | 10 | 字符、代码符号、大小写、数字、路径、标点准确性。 |
| `indentation_alignment_0_10` | 10 | 缩进、嵌套层级、表格/列表对齐。 |
| `structure_format_0_10` | 10 | 换行、代码块、列表、表格、区域结构。 |
| `reading_region_order_0_10` | 10 | 阅读顺序、区域顺序、多文本块顺序。 |
| `noise_and_usability_0_10` | 10 | 重复、幻觉、无关文本、解释性文字和实际可用性。 |

裁判原则仍是：

- 只比较 `label` 与 `prediction`。
- 不把 NED 传入裁判 prompt。
- 不奖励额外解释、推断、补全、格式美化或代码重写。
- 对代码符号、缩进、路径、命令参数、配置结构、diff 前缀和错误行号保持严格。

## v4 积分框架

v4 正式积分不再沿用 v3 的五项规则分作为最终分。v4 直接使用 LLM 六维评分，并把活动规则分类权重放入同一个公式；严格可用率、完成率、安全分和 severe 只作为诊断指标展示，不参与最终排序。

### 六维分类分

先对每个类别分别计算六个 LLM 子项的类别平均分，并归一化到 0-1。每个子项只使用一次，不再额外重复叠加最弱类别、类别标准差或严格可用率惩罚。

```text
category_score =
100 * (
  0.20 * content_coverage^1.4
+ 0.24 * symbol_accuracy^1.4
+ 0.16 * indentation_alignment^1.4
+ 0.14 * structure_format^1.4
+ 0.10 * reading_region_order^1.4
+ 0.16 * noise_and_usability^1.4
)
```

六维权重：

| LLM 维度 | 权重 | 说明 |
| --- | ---: | --- |
| 内容覆盖 | 20% | 主体文字、文件名、关键上下文是否保留。 |
| 符号准确性 | 24% | 代码符号、大小写、数字、路径、标点。 |
| 缩进与对齐 | 16% | Python、YAML、表格、树形结构等层级。 |
| 结构格式 | 14% | 换行、代码块、列表、表格列、错误堆栈结构。 |
| 阅读顺序 | 10% | 多区域、堆栈、diff、终端输出顺序。 |
| 噪声与可用性 | 16% | 重复、幻觉、解释性文字、包装文本和实际可用性。 |

指数 `1.4` 用于体现开发场景的非线性风险：7 分不是 70% 可用，而是仍需要明显人工修正；但每个子项仍只在公式中出现一次。

### 分类权重

参照 PaddleOCR Hackathon 规则中对真实场景、任务复杂度、场景稀缺性和评估集难度的强调，v4 降低相对规则化、普遍高分的类别权重，提高结构敏感和困难场景权重。

| 类别 | 权重 | 设计理由 |
| --- | ---: | --- |
| IDE 代码编辑器截图 | 15% | 主场景，代码和 UI 混合，复杂度中高。 |
| 终端 / Shell / PowerShell | 7% | 当前样本相对规则化，模型普遍较高分。 |
| 报错日志 / Traceback | 17% | 路径、行号、错误顺序错一处就影响排错。 |
| 配置文件 / YAML / JSON / TOML / INI | 14% | 缩进、冒号、引号、层级和布尔/数字敏感。 |
| Git diff / patch / PR 页面 | 7% | 当前样本规则性较强，普遍较高分。 |
| 网页代码块 / 文档代码块 | 10% | 中等复杂度，需避免混入页面正文。 |
| 表格化代码信息 / 参数表 / API 文档 | 12% | 列错位、漏参数会明显影响使用。 |
| 模糊、压缩、拍屏、暗色主题、小字号等困难样本 | 18% | 抗噪声、小字号、低对比是活动长尾价值。 |

最终分：

```text
final_score_v4 = sum(category_weight * category_score)
```

### 排名分组

提示词策略会显著改变模型行为，尤其是容易解释化或改写的通用 VLM。因此 v4 主报告必须按 `prompt_group` 分开排名：

| 分组 | 口径 | 排名用途 |
| --- | --- | --- |
| `short_prompt` | `<image>OCR:` | 主短提示榜，优先对比模型原生 OCR 倾向。 |
| `long_or_strict_prompt` | `strict_ocr_prompt` / `dev_ocr_prompt` | 长/严格提示榜，用于观察 prompt 约束后的能力，不与短提示榜混排。 |
| `other_prompt` | API 默认、layout API 或其他口径 | 只作诊断对照，必须明确说明。 |

`evaluations/benchmark_v4/benchmark_v4_results.md` 可以保留全部结果诊断表，但不得把不同 `prompt_group` 当作同一排行榜解释。

### 诊断指标

v4 报告保留以下诊断指标，但不进入最终分：

| 指标 | 用途 |
| --- | --- |
| `global_llm_dimension_score_v4` | 不按类别加权的全局六维分，仅作整体观察。 |
| `category_macro_score_v4` | 8 个类别分的简单平均，观察类别均衡性。 |
| `category_min_score_v4` | 最弱类别分数，暴露单类崩坏，但不重复进入公式。 |
| `category_std_v4` | 类别分数标准差，观察模型是否偏科，但不重复进入公式。 |
| `direct_usable_rate_pct` | 严格可用率，只用于解释结果。 |
| `completion_rate_pct` | 有效完成率，只用于解释空输出/不可用输出。 |
| `safety_score_pct` | 非 severe 样本比例，只用于解释风险。 |
| `severe_by_category` | 每类 severe badcase 数量。 |
| `top_error_tags` | 高频错误标签。 |

## Severe badcase

v4 第一版沿用 v3 severe 条件：

```text
severe =
    missing_record
    or sample_fidelity < 0.35
    or noise_and_usability_0_10 <= 1
    or score_0_100 < 40
    or any(front_five_dimension_ratio < 0.2)
    or error_tags contains code_added_removed_or_rewritten
```

v4 报告中要重点统计以下标签：

- `wrong_code_symbol`
- `wrong_number_or_path`
- `bad_line_break_or_indent`
- `broken_structure`
- `wrong_reading_order`
- `hallucinated_text`
- `repeated_output`
- `truncated_output`
- `code_added_removed_or_rewritten`

如果某个模型在任一类别中 severe 比例超过 40%，即使整体分不低，也必须在报告中标注为该类别不稳定。

## 评测流程

### 1. 生成模型预测

使用 v4 JSONL：

```powershell
python -B .\scripts\evaluate_openai_compatible_vl_testset.py `
  --data-path .\test.jsonl `
  --url http://127.0.0.1:8080/v1/chat/completions `
  --model <model_name> `
  --api-key EMPTY `
  --output evaluations/benchmark_v4/<run_name>_result.jsonl `
  --summary evaluations/benchmark_v4/<run_name>_summary.json `
  --errors evaluations/benchmark_v4/<run_name>_errors.jsonl `
  --use-sample-prompt `
  --max-tokens 8192 `
  --temperature 0 `
  --workers 1
```

要求：

- PaddleOCR-VL 系列主口径固定 `<image>OCR:`。
- vLLM 请求必须显式设置 `temperature=0`。
- 每个 checkpoint 至少扫 `max_tokens` 和 `repetition_penalty` 的少量组合。
- 输出文件名必须包含模型、提示词策略、关键推理参数和数据集版本。

### 2. LLM 裁判

```powershell
python -B .\scripts\judge_ocr_predictions_llm.py `
  --input evaluations/benchmark_v4/<run_name>_result.jsonl `
  --output evaluations/benchmark_v4/llm_judge_<run_name>_deepseek_v4_flash_v4.jsonl `
  --summary evaluations/benchmark_v4/llm_judge_<run_name>_deepseek_v4_flash_v4_summary.json `
  --errors evaluations/benchmark_v4/llm_judge_<run_name>_deepseek_v4_flash_v4_errors.jsonl `
  --url http://127.0.0.1:3000/v1/chat/completions `
  --model deepseek-v4-flash `
  --api-key-env OPENAI_API_KEY `
  --workers 5
```

### 3. 汇总 v4

已新增 `evaluate/build_benchmark_v4.py`，从历史评分逻辑复用核心指标后加入分类汇总：

- 默认 `TOTAL_SAMPLES = 100`。
- 默认输入目录 `evaluations/benchmark_v4/`。
- 默认 pattern 使用 `llm_judge_*_full100_*_deepseek_v4_flash_v4.jsonl`，避免新增 50 题等中间裁判文件混入正式总榜。
- 读取 `benchmark_v4_workspace/final_ui/by_category_manifest.jsonl` 建立 `image -> category` 映射。
- 输出整体 v4 排名和分类分表。
- 输出 `benchmark_v4_results.json`、`benchmark_v4_results.csv`、`benchmark_v4_results.md`。

建议命令：

```powershell
python -B .\scripts\build_benchmark_v4.py `
  --eval-dir evaluations/benchmark_v4 `
  --pattern "llm_judge_*_full100_*_deepseek_v4_flash_v4.jsonl" `
  --manifest .\benchmark_v4_workspace\final_ui\by_category_manifest.jsonl `
  --total-samples 100 `
  --out-json evaluations/benchmark_v4/benchmark_v4_results.json `
  --out-csv evaluations/benchmark_v4/benchmark_v4_results.csv `
  --out-md evaluations/benchmark_v4/benchmark_v4_results.md
```

## 报告格式

v4 总表至少展示：

| 字段 | 说明 |
| --- | --- |
| `final_score_v4` | 最终排序主指标。 |
| `global_llm_dimension_score_v4` | 不按类别加权的全局六维分。 |
| `category_macro_score_v4` | 8 类简单平均分，诊断用。 |
| `category_min_score_v4` | 最弱类别分，诊断用。 |
| `category_std_v4` | 类别分标准差，诊断用。 |
| `fidelity_score_pct` | 结构化 OCR 保真度诊断。 |
| `noise_usability_pct` | 噪声与可用性诊断。 |
| `direct_usable_rate_pct` | 严格可用率诊断。 |
| `completion_rate_pct` | 完成率诊断。 |
| `safety_score_pct` | 安全分诊断。 |
| `avg_llm_score` | 六维等权展示分，非排序主指标。 |
| `avg_ned` | 字符编辑距离参考，非排序主指标。 |
| `top_error_tags` | 高频错误标签。 |

每个模型还应附分类表：

```text
类别 | 权重 | 题数 | final_score_v4 | 保真度诊断 | 噪声可用性 | 严格可用率 | severe | 高频错误
```

## 第一阶段执行计划（历史记录）

以下内容是 v4 benchmark 建设早期的过程记录，用于说明测试集和评分规则如何形成；正式提交口径以本文档前部、`docs/ocr_benchmark_v4.md`、`README.md` 和模型卡中的 v6 结果为准。

1. 冻结 `benchmark_v4_workspace/final_ui/`，不再改图和真值。
2. 已新增 `evaluate/build_benchmark_v4.py`，复用 v3 评分函数并加入分类汇总。
3. 选择 2-3 个已知模型跑通 v4 全流程，优先用：
   - PaddleOCR-VL-1.6 微调 v2；
   - PaddleOCR-VL-1.6 微调 v5；
   - 一个外部强 VLM 短提示结果作为参考。
4. 对比 v3 与 v4 的相对排序，确认 v4 是否更能暴露配置、diff、终端和错误日志短板。
5. 抽样人工复核 LLM 裁判，重点看新类别中的误判：
   - diff 前缀 `+/-`；
   - YAML / TOML 缩进；
   - traceback 顺序；
   - 表格列错位；
   - 终端长输出裁切；
   - 文档代码块是否混入页面正文。
6. 固化 `benchmark_v4_results.md` 的展示格式。

当前已完成 PaddleOCR-VL-1.6 微调 v5 和 Qwen3.6 Flash 的补测：旧 50 题沿用历史裁判结果，新增 50 题重新跑 OCR 与 LLM 裁判后合并为 100 题 v4 结果。

| 文件 | 内容 |
| --- | --- |
| `evaluations/benchmark_v4/test_v4_added_50.jsonl` | 新增 50 题评测入口。 |
| `evaluations/benchmark_v4/ppocr_vl16_5_added50_4096_rp105_temp0_result.jsonl` | v5 对新增 50 题的 OCR 输出。 |
| `evaluations/benchmark_v4/llm_judge_ppocr_vl16_5_added50_4096_rp105_temp0_deepseek_v4_flash_v4.jsonl` | 新增 50 题 LLM 裁判结果。 |
| `evaluations/benchmark_v4/llm_judge_ppocr_vl16_5_full100_4096_rp105_temp0_deepseek_v4_flash_v4.jsonl` | 合并后的 100 题 LLM 裁判结果。 |
| `evaluations/benchmark_v4/qwen36flash_added50_sampleprompt_result.jsonl` | Qwen3.6 Flash 对新增 50 题的 OCR 输出。 |
| `evaluations/benchmark_v4/llm_judge_qwen36flash_added50_sampleprompt_deepseek_v4_flash_v4.jsonl` | Qwen3.6 Flash 新增 50 题 LLM 裁判结果。 |
| `evaluations/benchmark_v4/llm_judge_qwen36flash_full100_sampleprompt_deepseek_v4_flash_v4.jsonl` | Qwen3.6 Flash 合并后的 100 题 LLM 裁判结果。 |
| `evaluations/benchmark_v4/benchmark_v4_results.md` | v4 总榜，正式结果已扩展为多个 full100 run，并按提示词分组排名。 |
| `evaluations/benchmark_v4/benchmark_v4_ppocr_vl16_5_results.md` | v5 单模型 v4 汇总报告。 |
| `evaluations/benchmark_v4/benchmark_v4_qwen36flash_results.md` | Qwen3.6 Flash 单模型 v4 汇总报告。 |

首轮 v4 结果：

| 方案 | 记录 | 最终积分 v4 | 全局六维分 | 类别宏平均 | 最弱类别 | 保真度诊断 | 噪声可用性 | 严格可用率 | 完成率 | 安全分 | 平均 LLM | 平均 NED |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3.6 Flash `<image>OCR:` | 100/100 | 66.29 | 68.71 | 68.73 | 54.52 | 75.53% | 71.50% | 58.00% | 94.00% | 74.00% | 77.04 | 0.1387 |
| PaddleOCR-VL-1.6 微调 v5 更新 checkpoint `max_tokens=4096, rp=1.05, temperature=0` | 100/100 | 51.53 | 56.03 | 56.45 | 24.93 | 63.64% | 59.70% | 40.00% | 94.00% | 75.00% | 66.89 | 0.1729 |
| PaddleOCR-VL-1.6 微调 v5 `max_tokens=4096, rp=1.05, temperature=0` | 100/100 | 49.76 | 54.78 | 54.40 | 19.32 | 62.17% | 59.00% | 33.00% | 96.00% | 72.00% | 66.07 | 0.1676 |

Qwen3.6 Flash 分类表现：

| 类别 | 权重 | 记录 | final_score_v4 | severe | 结论 |
| --- | ---: | ---: | ---: | ---: | --- |
| 终端 / Shell / PowerShell | 7% | 15/15 | 84.65 | 0 | 当前最稳类别，但因相对规则化权重较低。 |
| Git diff / patch / PR 页面 | 7% | 10/10 | 80.14 | 1 | diff/patch 表现稳定，但复杂 combined diff 仍可能破坏结构。 |
| 配置文件 / YAML / JSON / TOML / INI | 14% | 15/15 | 69.14 | 5 | 总体强于本地 v5，但仍有重写配置和缩进风险。 |
| IDE 代码编辑器截图 | 15% | 20/20 | 68.27 | 6 | 主体覆盖较好，漏文本和代码符号错误仍多。 |
| 表格化代码信息 / 参数表 / API 文档 | 12% | 5/5 | 66.40 | 2 | 明显优于本地 v5，但小类仍有幻觉和改写风险。 |
| 网页代码块 / 文档代码块 | 10% | 10/10 | 65.11 | 3 | 大部分可用，但长文档代码块偶发解释/漏识别。 |
| 模糊、压缩、拍屏、暗色主题、小字号等困难样本 | 18% | 10/10 | 61.60 | 3 | 强于本地 v5，但权重高，因此仍显著影响总分。 |
| 报错日志 / Traceback | 17% | 15/15 | 54.52 | 6 | 最弱类别，主要问题是解释性输出、包装文本、幻觉和错误信息改写。 |

PaddleOCR-VL-1.6 微调 v5 旧 checkpoint 分类表现：

| 类别 | 权重 | 记录 | final_score_v4 | severe | 结论 |
| --- | ---: | ---: | ---: | ---: | --- |
| Git diff / patch / PR 页面 | 7% | 10/10 | 80.95 | 0 | 当前最稳，但权重较低。 |
| 终端 / Shell / PowerShell | 7% | 15/15 | 70.29 | 1 | 命令和终端输出相对稳定。 |
| 网页代码块 / 文档代码块 | 10% | 10/10 | 63.60 | 2 | 可用但仍有符号和结构错误。 |
| IDE 代码编辑器截图 | 15% | 20/20 | 55.91 | 6 | 主体可读，缩进、符号和漏文本仍明显。 |
| 配置文件 / YAML / JSON / TOML / INI | 14% | 15/15 | 52.87 | 4 | 嵌套结构、引号、冒号和缩进仍是主要风险。 |
| 报错日志 / Traceback | 17% | 15/15 | 49.43 | 5 | 堆栈顺序和路径/行号仍需加强。 |
| 表格化代码信息 / 参数表 / API 文档 | 12% | 5/5 | 42.86 | 2 | 小类波动大，表格列对齐和漏文本影响明显。 |
| 模糊、压缩、拍屏、暗色主题、小字号等困难样本 | 18% | 10/10 | 19.32 | 8 | 当前最大短板，且权重最高。 |

## 验收标准

v4 规划进入正式口径前，需要满足：

- 至少 3 个模型完整跑通 100 题，无异常缺失。
- LLM 裁判输出均为 `dev_ocr_judge_v4`，不混用旧 prompt。
- `evaluate/build_benchmark_v4.py` 能重复生成 JSON、CSV、Markdown。
- 总分、分类分和 severe 统计能解释主要模型差异。
- 抽样人工复核未发现系统性裁判偏差。
- 对外文档明确 v3 与 v4 的区别，避免把两个榜单混排。

## 当前结论

v4 不改 LLM 裁判，但最终公式已改为分类加权六维分。这样既保留 v3 六维裁判经验，又让活动规则中的真实复杂场景、长尾困难样本和结构敏感样本直接影响总分。

该阶段使用 PaddleOCR-VL-1.6 模型 v6。模型 v6 使用 `<image>OCR:`、`max_tokens=4096`、`repetition_penalty=1.08`、`temperature=0`，在 Benchmark v4 固定 100 题上的 `final_score_v4` 为 `61.08`。模型 v5 / v2 表格保留为历史开发记录；当前公开结果以 Benchmark v5 内容版本 5.2 为准。
