#!/bin/bash
# Pre-commit hooks 설정 (uv 전용)
# backend 디렉터리에서 실행하거나, 프로젝트 루트의 scripts/setup-pre-commit.sh 사용 권장

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1

echo "🔧 Pre-commit hooks 설정 (uv 전용)..."
echo "   💡 통합 설정은 프로젝트 루트에서 실행하세요: ./scripts/setup-pre-commit.sh"
echo ""

if ! command -v uv &> /dev/null; then
    echo "   ❌ uv가 설치되어 있지 않습니다. 설치: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
if [ ! -d ".venv" ]; then
    echo "   ❌ .venv가 없습니다. uv venv && uv pip install -r requirements-dev.txt"
    exit 1
fi

if ! .venv/bin/pre-commit --version &> /dev/null; then
    echo "📦 pre-commit 설치 중..."
    uv pip install pre-commit
    echo "   ✅ pre-commit 설치 완료"
fi

echo "📝 Pre-commit hooks 설치 중..."
.venv/bin/pre-commit install
echo "   ✅ Pre-commit hooks 설정 완료"
echo ""
echo "💡 수동 실행: uv run pre-commit run --all-files"
