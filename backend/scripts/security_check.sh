#!/bin/bash
# 의존성 취약점 스캔 스크립트 (uv 전용, backend 디렉터리에서 실행)

set -e

echo "🔒 보안 취약점 스캔 시작..."

if ! command -v uv &> /dev/null; then
    echo "   ❌ uv가 필요합니다. 설치: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
if [ ! -d ".venv" ]; then
    echo "   ❌ .venv가 없습니다. uv venv && uv pip install -r requirements-dev.txt"
    exit 1
fi

if ! .venv/bin/safety --version &> /dev/null 2>&1; then
    echo "📦 safety 설치 중..."
    uv pip install safety
fi

echo ""
echo "📋 Python 의존성 취약점 스캔 중..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "requirements.txt" ]; then
    echo "📄 requirements.txt 스캔 중..."
    uv run safety check --file requirements.txt || echo "⚠️  requirements.txt에서 취약점 발견"
fi
if [ -f "requirements-dev.txt" ]; then
    echo "📄 requirements-dev.txt 스캔 중..."
    uv run safety check --file requirements-dev.txt || echo "⚠️  requirements-dev.txt에서 취약점 발견"
fi

echo ""
echo "✅ 보안 스캔 완료!"
echo "💡 업데이트 확인: uv pip list --outdated"
