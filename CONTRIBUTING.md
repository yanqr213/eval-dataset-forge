# 贡献指南 / Contributing

## 中文

欢迎贡献 Eval Dataset Forge。项目刻意保持小而清晰，贡献时请优先保证 CLI 可预测、本地优先、适合在 CI 中运行。

## 本地开发

```bash
python -m pip install -e .
python -m unittest discover -s tests
```

## 贡献原则

- 除非能显著降低复杂度，否则不要增加运行时依赖。
- 保持 shuffle 和 split 的确定性。
- 新增校验规则、CLI 参数或输出格式时补充测试。
- 行为变化时同步更新 `README.md`。
- 核心构建流程不要加入网络调用。
- 不要提交密钥、私有 eval 数据或生成产物。

## English

Thanks for improving Eval Dataset Forge. The project is intentionally small, so contributions should keep the CLI predictable, local-first, and easy to run in CI.

## Development Setup

```bash
python -m pip install -e .
python -m unittest discover -s tests
```

## Contribution Guidelines

- Keep runtime dependencies at zero unless a dependency removes substantial complexity.
- Preserve deterministic behavior for shuffle and split operations.
- Add tests for new validation rules, CLI arguments, or output formats.
- Keep input/output schemas documented in `README.md`.
- Do not add network calls to the core build path.
- Avoid committing secrets, private eval data, or generated outputs.
