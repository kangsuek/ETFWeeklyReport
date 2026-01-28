#!/bin/bash
# 프론트엔드 의존성 취약점 스캔 스크립트

set -e

echo "🔒 Node.js 의존성 취약점 스캔 시작..."

if [ ! -f "package.json" ]; then
    echo "❌ package.json을 찾을 수 없습니다."
    exit 1
fi

echo ""
echo "📋 npm audit 실행 중..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# npm audit 실행 (moderate 이상만)
npm audit --audit-level=moderate || {
    echo ""
    echo "⚠️  취약점이 발견되었습니다."
    echo ""
    echo "💡 자동 수정 시도:"
    echo "   npm audit fix"
    echo ""
    echo "💡 수동 수정이 필요한 경우:"
    echo "   npm audit"
    exit 1
}

echo ""
echo "✅ 보안 스캔 완료!"
