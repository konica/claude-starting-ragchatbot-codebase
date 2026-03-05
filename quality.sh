#\!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: ./quality.sh [--fix]"
    echo ""
    echo "Run code quality checks on the backend."
    echo ""
    echo "Options:"
    echo "  --fix    Auto-format files instead of just checking"
    exit 1
}

FIX=false
for arg in "$@"; do
    case "$arg" in
        --fix) FIX=true ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $arg"; usage ;;
    esac
done

echo "=== Black (code formatting) ==="
if [ "$FIX" = true ]; then
    uv run black backend/
else
    uv run black --check backend/
fi

echo ""
echo "All checks passed\!"
