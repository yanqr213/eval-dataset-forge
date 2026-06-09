# 更新日志 / Changelog

## 中文

所有重要变更都会记录在这里。

## [0.2.0] - 2026-06-09

### 新增

- 新增 `card` 命令，可生成 Markdown dataset card 或 JSON manifest。
- dataset card 包含数据集哈希、字段覆盖率、标签/metadata 分布、重复记录统计和校验警告。
- GitHub Actions 增加 dataset card smoke test。

## [0.1.0] - 2026-06-07

### 新增

- 初始 Python 包，采用 `src/` 项目结构。
- `validate`、`build`、`split`、`stats` CLI 命令。
- 支持 JSON、JSONL、CSV 输入。
- 支持 JSON、JSONL、CSV 输出。
- 校验必填字段 `id`、`prompt`、`expected`。
- 规范化可选字段 `metadata` 和 `tags`。
- 支持稳定随机种子的 shuffle 和 train/validation/test 切分。
- 支持按 `id` 或 prompt/expected 内容去重。
- 补充示例数据、单元测试和 GitHub Actions CI。

## English

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-06-09

### Added

- Added the `card` command for Markdown dataset cards and JSON manifests.
- Dataset cards include dataset hashes, field coverage, tag/metadata distributions, duplicate counts, and validation warnings.
- Added GitHub Actions smoke coverage for dataset card generation.

## [0.1.0] - 2026-06-07

### Added

- Initial Python package using a `src/` layout.
- `validate`, `build`, `split`, and `stats` CLI commands.
- JSON, JSONL, and CSV input support.
- JSON, JSONL, and CSV output support.
- Required field validation for `id`, `prompt`, and `expected`.
- Optional `metadata` and `tags` normalization.
- Stable seeded shuffle and train/validation/test splitting.
- Deduplication by `id` or prompt/expected content.
- Example datasets, unit tests, and GitHub Actions CI.
