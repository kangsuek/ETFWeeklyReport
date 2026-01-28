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

# Python 및 pip 명령어 확인
PYTHON_CMD=""
PIP_CMD=""

# 백엔드 가상환경 확인
if [ -d "backend/venv" ]; then
    echo "📦 백엔드 가상환경 발견, 활성화 중..."
    if source backend/venv/bin/activate 2>/dev/null; then
        PYTHON_CMD="python"
        PIP_CMD="pip"
        echo "   ✅ 가상환경 활성화 완료"
    else
        echo "   ⚠️  가상환경 활성화 실패, 시스템 Python 사용"
        PYTHON_CMD="python3"
        PIP_CMD="pip3"
    fi
else
    echo "   ⚠️  백엔드 가상환경이 없습니다. 시스템 Python 사용"
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
fi

# Python 명령어 확인
if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo "   ❌ $PYTHON_CMD 명령어를 찾을 수 없습니다."
    echo "   💡 Python을 설치하거나 가상환경을 생성하세요:"
    echo "      cd backend && python3 -m venv venv"
    exit 1
fi

# pip 명령어 확인
if ! command -v "$PIP_CMD" &> /dev/null; then
    echo "   ❌ $PIP_CMD 명령어를 찾을 수 없습니다."
    echo "   💡 pip를 설치하세요: $PYTHON_CMD -m ensurepip --upgrade"
    exit 1
fi

echo "   ✅ Python: $PYTHON_CMD ($($PYTHON_CMD --version))"
echo "   ✅ pip: $PIP_CMD ($($PIP_CMD --version))"

# Pre-commit 설치 확인
if ! command -v pre-commit &> /dev/null; then
    echo "📦 pre-commit 설치 중..."
    if ! $PIP_CMD install pre-commit; then
        echo "   ❌ pre-commit 설치 실패"
        exit 1
    fi
    echo "   ✅ pre-commit 설치 완료"
else
    echo "   ✅ pre-commit 이미 설치됨 ($(pre-commit --version))"
fi

# Pre-commit hooks 설치
echo "📝 Pre-commit hooks 설치 중..."
if pre-commit install; then
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
echo "💡 백엔드 가상환경이 활성화되지 않은 경우:"
echo "  cd backend && source venv/bin/activate  # macOS/Linux"
echo "  cd backend && venv\\Scripts\\activate     # Windows"
