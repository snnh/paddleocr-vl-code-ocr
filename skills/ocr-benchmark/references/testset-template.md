# OCR 测试集文件结构模板

本模板只规定推荐关系，不固定测试集名称、根目录、类别、难度或样本数。复制时按当前项目的评测脚本调整字段。

## 目录

- [最小结构](#最小结构)
- [扩展结构](#扩展结构)
- [manifestjsonl 示例](#manifestjsonl-示例)
- [testjsonl 示例](#testjsonl-示例)
- [tagstsv 示例](#tagstsv-示例)
- [审计文件建议](#审计文件建议)
- [冻结前检查](#冻结前检查)

## 最小结构

适合只需要图片、真值和 JSONL 入口的评测：

```text
<testset-root>/
├── images/
│   ├── sample_000001.png
│   └── sample_000002.jpg
├── annotations/
│   ├── sample_000001.txt
│   └── sample_000002.txt
├── manifest.jsonl
└── test.jsonl
```

约束：

- 图片与标注使用相同 stem，或由 manifest 明确映射。
- `.txt` 保存图片中应转写的可见文字，统一使用 UTF-8 和 LF。
- `manifest.jsonl` 每条记录对应一个唯一样本。
- `test.jsonl` 使用评测脚本实际支持的对话或任务格式。

## 扩展结构

适合需要分类、难度、视觉标签、来源和冻结审计的正式 benchmark：

```text
<testset-root>/
├── images/
│   └── <difficulty>/
│       └── <category>/
│           └── <sample-id>.<image-ext>
├── annotations/
│   └── <difficulty>/
│       └── <category>/
│           └── <sample-id>.txt
├── audit/
│   ├── checksums.tsv
│   ├── sources.jsonl
│   ├── quality_audit.tsv
│   └── freeze_summary.json
├── manifest.jsonl
├── test.jsonl
├── test.json
├── tags.tsv
├── FREEZE.md
└── data_statement.md
```

`<difficulty>`、`<category>` 和图片扩展名都是占位符。项目不使用分类或难度时，可去掉对应层级，但 manifest 中的路径必须与磁盘一致。

## manifest.jsonl 示例

每行一个 JSON 对象：

```json
{"id":"sample_000001","image":"images/medium/code/sample_000001.png","annotation":"annotations/medium/code/sample_000001.txt","image_sha256":"<sha256>","annotation_sha256":"<sha256>","category":"code","difficulty":"medium","source_type":"self_collected","review_status":"approved"}
```

建议字段：

| 字段 | 必需 | 含义 |
| --- | --- | --- |
| `id` | 是 | 全测试集唯一 ID |
| `image` | 是 | 相对测试集根目录的图片路径 |
| `annotation` | 是 | 相对测试集根目录的真值路径 |
| `image_sha256` | 建议 | 图片内容指纹 |
| `annotation_sha256` | 建议 | 标注内容指纹 |
| `category` | 可选 | 项目自定义类别 |
| `difficulty` | 可选 | 项目自定义难度 |
| `source_type` | 建议 | 来源类型或采集方式 |
| `review_status` | 建议 | 人工审核状态 |

计分脚本使用其他字段名时，以脚本和 benchmark 规则为准，不为套模板强改字段。

## test.jsonl 示例

OpenAI-compatible 图文对话格式示例：

```json
{"images":["./images/medium/code/sample_000001.png"],"messages":[{"role":"user","content":"<image>OCR:"},{"role":"assistant","content":"print(\"hello\")"}]}
```

若评测器使用 `image`、`label`、CSV 或目录扫描格式，转换模板而不是要求评测器接受本示例。

## tags.tsv 示例

标签只用于切片分析，不作为 OCR 真值：

```tsv
id	text_density	legibility	capture_type	risk_tags
sample_000001	medium	good	native_screenshot	small_text|syntax_dense
```

多值字段选择一种稳定分隔符，并在数据声明中写明；不要把字符串误拆成单字符标签。

## 审计文件建议

- `checksums.tsv`：冻结文件相对路径与 SHA-256。
- `sources.jsonl`：逐样本来源、许可、审核和哈希证据。
- `quality_audit.tsv`：缺图、空标注、坏编码、重复 ID、重复图片等检查结果。
- `freeze_summary.json`：数据集 ID、版本、样本数、分类难度分布和阻塞项。
- `FREEZE.md`：冻结日期、边界和变更规则。
- `data_statement.md`：来源、预标注、人工复核、防泄漏与许可说明。

## 冻结前检查

1. 图片、标注、manifest 和评测入口数量一致。
2. ID、图片哈希和路径唯一。
3. 图片与标注文件全部存在且可读。
4. 标注非空，编码和换行统一。
5. manifest 路径、类别、难度与磁盘一致。
6. 训练集与测试集图片哈希无重叠。
7. 人工审核状态满足当前发布门槛。
8. 根入口与测试集内部入口逻辑一致。
9. 修改图片或真值后生成新冻结版本，不原地冒充旧版本。
