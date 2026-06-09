# Eval Dataset Forge / 评测数据集锻造器

Eval Dataset Forge 是一个轻量级 Python CLI，用于把 JSON、JSONL 或 CSV 模板转换成经过校验的 LLM 评测数据集。它面向希望把 eval 数据纳入版本管理和 CI 的团队，不要求一开始就引入大型评测平台。

English documentation is included after the Chinese section.

## 项目定位

这是一个完整的本地优先数据工具，不是示例脚本。它帮助团队把评测样例整理成稳定、可审查、可重复生成的文件，便于在 CI、评测运行器和人工审查流程中使用。

## 能做什么

- 校验必填字段：`id`、`prompt`、`expected`。
- 规范化可选字段：`metadata` 和 `tags`。
- 支持按 `id` 或 prompt/expected 内容哈希去重。
- 使用稳定随机种子进行打乱和 train/validation/test 切分。
- 导出 JSON、JSONL 或 CSV。
- 生成 Markdown dataset card 或 JSON manifest，方便 PR 审查、CI artifact 和数据治理留痕。
- 运行时仅使用 Python 标准库。

## 真实使用场景

- 将聊天机器人、Agent 或 RAG 系统的回归测试 prompts 保存在代码仓库中。
- 把便于表格编辑的 CSV 模板转换为评测运行器需要的 JSONL。
- 在合并新 eval case 前，通过 CI 强制执行数据质量检查。
- 将一个人工维护的源文件稳定切分为 train、validation、test。
- 快速查看重复 ID、标签分布、metadata 字段等统计信息。
- 为每次 eval 数据变更生成可复现哈希和字段覆盖摘要，让 reviewer 不必逐行打开原始 prompt。

## 安装

需要 Python 3.10 或更高版本。

```bash
python -m pip install -e .
```

安装后可使用以下命令：

```bash
eval-dataset-forge --help
```

也可以在源码目录中通过 `PYTHONPATH` 直接运行：

```bash
PYTHONPATH=src python -m eval_dataset_forge --help
```

PowerShell：

```powershell
$env:PYTHONPATH = "src"
python -m eval_dataset_forge --help
```

## 常用命令

### 校验数据

```bash
python -m eval_dataset_forge validate examples/basic.json
```

`validate` 会检查输入结构、必填字段、可选字段类型和重复 ID。全部通过时退出码为 `0`，存在校验错误时退出码为 `1`。

### 构建数据集

```bash
python -m eval_dataset_forge build examples/basic.json -o outputs/eval.jsonl --shuffle --seed 123
```

`build` 会校验记录，默认跳过无效行，执行去重，可选按 `--seed` 稳定打乱，并输出 JSON、JSONL 或 CSV。使用 `--strict` 可以在发现无效行时直接失败，而不是跳过。

### 切分数据集

```bash
python -m eval_dataset_forge split examples/basic.json -o outputs/splits --train 0.8 --validation 0.1 --test 0.1 --seed 123
```

`split` 会构建清洗后的数据集，并输出 `train`、`validation`、`test` 文件。比例之和必须为 `1.0`。

### 输出统计信息

```bash
python -m eval_dataset_forge stats examples/basic.json
```

`stats` 输出 JSON 统计信息，包括记录数量、重复 ID、平均 prompt 长度、标签计数和 metadata key 计数。

### 生成 Dataset Card

```bash
python -m eval_dataset_forge card examples/basic.json \
  --name "support regression eval" \
  --purpose "PR eval review" \
  --owner "quality" \
  --format markdown \
  --output outputs/dataset-card.md
```

`card` 会输出适合放进 PR 评论、CI summary 或 artifact 的 dataset card。它包含数据集哈希、字段覆盖率、标签分布、metadata key 分布、重复记录统计、样本 ID 摘要和校验警告。为了降低泄漏风险，Markdown card 不复制 `prompt` 或 `expected` 原文。

如果需要给自动化系统读取，可以生成 JSON manifest：

```bash
python -m eval_dataset_forge card examples/basic.json \
  --format json \
  --output outputs/dataset-card.json
```

在 CI 中可以加 `--check`，当 card 中存在 warning 时返回退出码 `1`。

## 输入格式

每条记录必须包含：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | string | 是 | eval case 的稳定唯一标识。 |
| `prompt` | string | 是 | 发送给模型或评测目标的输入。 |
| `expected` | string | 是 | 期望答案、标签、rubric 结果或参考回复。 |
| `metadata` | object | 否 | 结构化上下文，例如类别、来源、难度、负责人或模型家族。 |
| `tags` | string array | 否 | 可搜索标签，例如 `qa`、`safety`、`rag` 或 `classification`。 |

JSON 可以是记录数组，也可以是包含 `records` 数组的对象。

```json
[
  {
    "id": "qa-capital-fr",
    "prompt": "What is the capital of France?",
    "expected": "Paris",
    "metadata": {
      "category": "geography",
      "difficulty": "easy"
    },
    "tags": ["qa", "factual"]
  }
]
```

CSV 必须包含表头。`metadata` 应为 JSON object 字符串，`tags` 可以是逗号分隔字符串，也可以是 JSON array 字符串。

```csv
id,prompt,expected,metadata,tags
qa-capital-jp,What is the capital of Japan?,Tokyo,"{""category"": ""geography""}","qa,factual"
```

## 输出格式

JSON 输出为格式化后的规范化记录数组。JSONL 每行写入一条规范化 JSON object。CSV 输出必填字段，并将 `metadata` 和 `tags` 编码为 JSON 字符串。

规范化输出保证：

- `id`、`prompt`、`expected` 都是去除首尾空白的字符串。
- `metadata` 始终是 object。
- `tags` 始终是排序并去重后的字符串数组。
- 去重时保留第一条匹配记录。

Dataset card 输出格式：

- `markdown`: 面向 reviewer 的审查卡片，适合 PR 评论和 CI summary。
- `json`: 机器可读 manifest，适合归档、比对和数据治理流水线。

两种格式都会包含 `dataset_hash`。该哈希基于规范化并按 `--dedupe-key` 去重后的记录生成，可用于确认某次 eval 数据构建是否可复现。

## CI 示例

```yaml
- name: Validate eval data
  run: |
    eval-dataset-forge validate evals/source.json
    eval-dataset-forge build evals/source.json -o artifacts/eval.jsonl --shuffle --seed 123
    eval-dataset-forge card evals/source.json \
      --name "PR eval dataset" \
      --purpose "prompt regression gate" \
      --format markdown \
      --output artifacts/dataset-card.md \
      --check

- name: Upload dataset card
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: eval-dataset-card
    path: artifacts/dataset-card.md
```

## 隐私

Eval Dataset Forge 以本地运行为核心。它不会调用外部服务，不会上传数据，也不需要 API key 或 GitHub token。请将 eval 数据集视为潜在敏感数据，因为 prompts 可能包含客户示例、内部策略或专有 expected outputs。

建议实践：

- 发布前审查源文件。
- 避免提交密钥、客户隐私数据或生产日志。
- 使用 metadata 跟踪数据来源和审查状态。
- 在 CI 中运行 `validate` 后再合并数据变更。

## 项目结构

```text
.
├── .github/workflows/ci.yml
├── examples/
├── src/eval_dataset_forge/
│   ├── cli.py
│   └── core.py
├── tests/
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
└── pyproject.toml
```

## 测试

```bash
python -m unittest discover -s tests
```

## 限制

- 本工具不会执行模型调用，也不会进行评分。
- 除 `id`、`prompt`、`expected` 之外，它不强行定义通用 eval schema。
- 本工具不负责文件加密或密钥管理。
- 切分时 train 和 validation 使用向下取整，剩余记录进入 test。
- 超大文件会被加载到内存中，适合中小型 eval 数据集，不针对多 GB 语料优化。

## 许可证

MIT。详见 [LICENSE](./LICENSE)。

## English

Eval Dataset Forge is a small, dependency-light Python CLI for turning JSON, JSONL, or CSV templates into validated LLM evaluation datasets. It is built for teams that want reproducible eval data in source control and CI without adopting a large evaluation platform before they need one.

### Positioning

This is a complete local-first data utility, not a sample script. It helps teams keep evaluation cases stable, reviewable, and reproducibly generated for CI jobs, eval runners, and human review workflows.

### What It Does

- Validates required eval fields: `id`, `prompt`, and `expected`.
- Normalizes optional `metadata` and `tags` fields.
- Deduplicates by `id` or by prompt/expected content hash.
- Shuffles and splits data with stable random seeds.
- Exports JSON, JSONL, or CSV.
- Generates Markdown dataset cards or JSON manifests for pull request review, CI artifacts, and data governance.
- Uses only the Python standard library at runtime.

### Real Use Cases

- Keep regression prompts for a chatbot, agent, or RAG system in a repository.
- Convert spreadsheet-friendly CSV templates into JSONL files consumed by an eval runner.
- Enforce data quality in CI before merging new evaluation cases.
- Split one curated source file into reproducible train, validation, and test files.
- Generate quick stats for review, such as duplicate IDs, tag distribution, and metadata keys.
- Attach a reproducible dataset hash and coverage summary to every eval data change.

### Installation

Requires Python 3.10 or newer.

```bash
python -m pip install -e .
eval-dataset-forge --help
```

You can also run it directly from a checkout:

```bash
PYTHONPATH=src python -m eval_dataset_forge --help
```

### Commands

Validate an example dataset:

```bash
python -m eval_dataset_forge validate examples/basic.json
```

Build JSONL output with a stable shuffle:

```bash
python -m eval_dataset_forge build examples/basic.json -o outputs/eval.jsonl --shuffle --seed 123
```

Split into train, validation, and test files:

```bash
python -m eval_dataset_forge split examples/basic.json -o outputs/splits --train 0.8 --validation 0.1 --test 0.1 --seed 123
```

Print statistics:

```bash
python -m eval_dataset_forge stats examples/basic.json
```

Generate a dataset card:

```bash
python -m eval_dataset_forge card examples/basic.json \
  --name "support regression eval" \
  --purpose "PR eval review" \
  --format markdown \
  --output outputs/dataset-card.md
```

Generate a machine-readable manifest:

```bash
python -m eval_dataset_forge card examples/basic.json \
  --format json \
  --output outputs/dataset-card.json
```

Use `--check` in CI to return exit code `1` when the generated card contains warnings.

### Input Format

Each record must include `id`, `prompt`, and `expected`. Optional fields are `metadata` as an object and `tags` as a string array. JSON can be a list of records or an object containing a `records` list. CSV must include a header row; `metadata` should be a JSON object string, and `tags` can be either a comma-separated string or a JSON array string.

### Output Format

JSON output is a pretty-printed list of normalized records. JSONL writes one normalized JSON object per line. CSV writes required fields plus JSON-encoded `metadata` and `tags`.

Normalized output guarantees trimmed required strings, object-shaped metadata, sorted and deduplicated tags, and first-match preservation during deduplication.

Dataset cards are available as Markdown for reviewers or JSON for automation. They include a reproducible `dataset_hash`, field coverage, tag and metadata-key distributions, duplicate counts, sample ID summaries, and validation warnings. Markdown cards intentionally omit prompt and expected text to reduce accidental leakage in PR comments.

### Privacy

Eval Dataset Forge is local-first. It does not call external services, upload data, or require API keys. Treat eval datasets as potentially sensitive because prompts may contain customer examples, internal policies, or proprietary expected outputs.

### Testing

```bash
python -m unittest discover -s tests
```

### Limitations

- The tool does not execute model calls or score outputs.
- It does not define a universal eval schema beyond the required fields.
- It does not encrypt files or manage secrets.
- Split sizes use integer floors for train and validation; remaining records go to test.
- Very large files are loaded in memory and are not optimized for multi-gigabyte corpora.

### License

MIT. See [LICENSE](./LICENSE).
