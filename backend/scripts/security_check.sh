#!/bin/bash
# 의존성 취약점 스캔 스크립트

set -e

echo "🔒 보안 취약점 스캔 시작..."

# Safety 설치 확인
if ! command -v safety &> /dev/null; then
    echo "📦 safety 설치 중..."
    pip install safety
fi

echo ""
echo "📋 Python 의존성 취약점 스캔 중..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# requirements.txt 스캔
if [ -f "requirements.txt" ]; then
    echo "📄 requirements.txt 스캔 중..."
    safety check --file requirements.txt || echo "⚠️  requirements.txt에서 취약점 발견"
fi

# requirements-dev.txt 스캔
if [ -f "requirements-dev.txt" ]; then
    echo "📄 requirements-dev.txt 스캔 중..."
    safety check --file requirements-dev.txt || echo "⚠️  requirements-dev.txt에서 취약점 발견"
fi

echo ""
echo "✅ 보안 스캔 완료!"
echo ""
echo "💡 취약점이 발견되면 다음 명령으로 업데이트 가능한 패키지 확인:"
echo "   pip list --outdated"
