# OCR Benchmark 排行榜

更新时间：{{updated_at}}

## 评测口径

| 项目 | 值 |
| --- | --- |
| 测试集 | {{dataset_id_or_path}} |
| 预期样本数 | {{expected_records}} |
| 计分版本 | {{scoring_version}} |
| 裁判模型 | {{judge_model_id}} |
| 裁判 reasoning | {{judge_reasoning_mode}} |
| 裁判提示词版本 | {{judge_prompt_version}} |

不同测试集、提示词组或不兼容裁判口径必须分表，不得混排。

## {{prompt_group}} 排行

| 排名 | 方案 | thinking | API 来源 | 记录 | 最终积分 | 原始积分 | 分类加权 | 全局均值 | 最弱分类 | 最弱难度 | 严格可用率 | 完成率 | 安全分 | 平均 NED | 报告 | 备注 |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | {{model_name}} | {{thinking_mode}} | {{model_source_label}} | {{scored}}/{{expected}} | {{final_score}} | {{raw_score}} | {{category_weighted}} | {{global_mean}} | {{weakest_category}} | {{weakest_difficulty}} | {{direct_usable_rate}} | {{completion_rate}} | {{safety_score}} | {{avg_ned}} | [报告]({{report_link}}) | {{note}} |

## 分类最佳

| 分类 | 最佳方案 | 得分 | 样本数 |
| --- | --- | ---: | ---: |
| {{category}} | {{model_name}} | {{score}} | {{count}} |

## 难度最佳

| 难度 | 最佳方案 | 得分 | Severe |
| --- | --- | ---: | ---: |
| {{difficulty}} | {{model_name}} | {{score}} | {{severe_rate}} |

## 结论

- {{根据最终积分总结排名，不用小于裁判误差的差距做过度结论。}}
- {{解释高分与主要风险指标之间的关系。}}
- {{注明缺失记录、混合补跑参数或其他影响可比性的事项。}}
