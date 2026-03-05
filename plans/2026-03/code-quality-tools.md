# Code Quality Tools

## Context

The project has no code formatting or linting tools configured. All 9 backend Python files and 1 test file have inconsistent formatting. Adding Black for automatic formatting and a dev script for running quality checks will establish consistent code style and make it easy to maintain going forward.

## Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml` | Add `black` as dev dependency; add `[tool.black]` configuration section |
| `backend/*.py` (9 files) | Auto-format with Black |
| `backend/tests/test_ai_generator.py` | Auto-format with Black |
| `quality.sh` (new) | Dev script to run formatting checks |

## Implementation Steps

1. **Add Black as a dev dependency**
   - `uv add --dev black`

2. **Configure Black in `pyproject.toml`**
   - Set `line-length = 88` (Black default)
   - Target Python 3.13

3. **Run Black on the entire backend**
   - `uv run black backend/`
   - This formats all `.py` files in one pass

4. **Create `quality.sh` dev script**
   - `black --check backend/` — verify formatting
   - `black backend/` — auto-fix formatting
   - Support `--fix` flag to auto-format vs just check

5. **Update CLAUDE.md** with new commands section for quality checks

## Verification

1. Run `uv run black --check backend/` — should pass with zero reformatted files
2. Run `./quality.sh` — should report all files are well-formatted
3. Run `uv run pytest backend/tests/` — existing tests still pass
