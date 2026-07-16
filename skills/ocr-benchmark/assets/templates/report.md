# {{model_name}} OCR Benchmark 测评报告

更新时间：{{updated_at}}

## 先说结论

{{用一至三段说明最终分、所在档位、是否可直接用于 OCR，以及决定成绩的主要证据。}}

## 优势：它真正擅长什么

{{结合分类、难度、维度分和具体样本说明优势。不要写模型性格。}}

## 不足：它会怎样失败

{{说明主要错误类型、出现频率、典型场景和实际后果。区分事实与推断。}}

## 评测信息

| 项目 | 值 |
| --- | --- |
| 模型 | {{model_name}} |
| thinking | {{thinking_mode}} |
| API 来源 | {{model_source_label}} |
| 测试集 | {{dataset_id_or_path}} |
| 样本数 | {{scored_records}} / {{expected_records}} |
| 提示词组 | {{prompt_group}} |
| 关键参数 | {{request_parameters}} |
| 裁判模型 | {{judge_model_id}} |
| 裁判 reasoning | {{judge_reasoning_mode}} |
| 裁判提示词版本 | {{judge_prompt_version}} |

## 关键指标

| 指标 | 结果 |
| --- | ---: |
| 最终积分 | {{final_score}} |
| 原始积分 | {{raw_score}} |
| 分类加权分 | {{category_weighted_score}} |
| 全局均值 | {{global_mean_score}} |
| 严格可用率 | {{direct_usable_rate}} |
| 完成率 | {{completion_rate}} |
| 安全分 | {{safety_score}} |
| 平均 NED | {{avg_ned}} |
| Severe 比例 | {{severe_rate}} |
| 可靠性扣分 | {{reliability_penalty}} |

## 缺失与补跑

{{列出缺失样本、接口错误、补跑参数覆盖和最终处理。没有则写“无”。}}

## 详细结果

### 分类结果

| 分类 | 样本数 | 得分 | Severe |
| --- | ---: | ---: | ---: |
| {{category}} | {{count}} | {{score}} | {{severe_rate}} |

### 难度结果

| 难度 | 样本数 | 得分 | Severe |
| --- | ---: | ---: | ---: |
| {{difficulty}} | {{count}} | {{score}} | {{severe_rate}} |

### 主要错误标签

| 错误标签 | 次数 | 说明 |
| --- | ---: | --- |
| {{error_tag}} | {{count}} | {{impact}} |

### 典型 badcase

| 样本 ID | 分类 | 难度 | 问题 | 证据 |
| --- | --- | --- | --- | --- |
| {{sample_id}} | {{category}} | {{difficulty}} | {{failure}} | {{evidence}} |

> 详细逐样本结果：{{samples_artifact_path}}
