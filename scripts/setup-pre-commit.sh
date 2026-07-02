#!/bin/bash
# 통합 Pre-commit hooks 설정 스크립트
# 프로젝트 루트에서 실행

set -e

# 스크립트가 있는 디렉토리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

echo "🔧 통합 Pre-commit hooks 설정 중..."
echo "📂 프로젝트 루트: $PROJECT_ROOT"

# uv 전용: backend/.venv 필수
if ! command -v uv &> /dev/null; then
    echo "   ❌ uv가 설치되어 있지 않습니다. 설치: curl -LsSf https://astral.sh/uv/install.sh | sh 또는 brew install uv"
    exit 1
fi
if [ ! -d "backend/.venv" ]; then
    echo "   ❌ backend/.venv가 없습니다. 먼저 실행: cd backend && uv venv && uv pip install -r requirements-dev.txt"
    exit 1
fi

echo "📦 backend/.venv 사용 (uv)"
PYTHON_CMD="backend/.venv/bin/python"
PRECOMMIT_CMD="backend/.venv/bin/pre-commit"
echo "   ✅ Python: $PYTHON_CMD ($($PYTHON_CMD --version))"

if ! [ -f "backend/.venv/bin/pre-commit" ] || ! $PRECOMMIT_CMD --version &> /dev/null; then
    echo "📦 pre-commit 설치 중..."
    (cd backend && uv pip install pre-commit)
    PRECOMMIT_CMD="backend/.venv/bin/pre-commit"
    echo "   ✅ pre-commit 설치 완료"
else
    echo "   ✅ pre-commit 이미 설치됨 ($($PRECOMMIT_CMD --version))"
fi

# Pre-commit hooks 설치
echo "📝 Pre-commit hooks 설치 중..."
if $PRECOMMIT_CMD install; then
    echo "   ✅ Pre-commit hooks 설치 완료"
else
    echo "   ❌ Pre-commit hooks 설치 실패"
    exit 1
fi

echo ""
echo "✅ 통합 Pre-commit hooks 설정 완료!"
echo ""
echo "💡 사용법:"
echo "  - 커밋 시 자동으로 hooks 실행 (백엔드 + 프론트엔드 모두)"
echo "  - 수동 실행: pre-commit run --all-files"
echo "  - 특정 hook만 실행: pre-commit run <hook-id>"
echo ""
echo "💡 백엔드 환경이 없는 경우:"
echo "  cd backend && uv venv && uv pip install -r requirements-dev.txt"
