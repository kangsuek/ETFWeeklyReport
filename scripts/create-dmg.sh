#!/bin/bash

# ETF Weekly Report - DMG 생성 스크립트 (macOS)
# electron-builder를 사용하여 desktop/release 폴더에 DMG를 생성합니다.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_DIR="$PROJECT_ROOT/desktop"
OUTPUT_DIR="$DESKTOP_DIR/release"

echo "📦 ETF Weekly Report DMG 빌드"
echo "   프로젝트 루트: $PROJECT_ROOT"
echo ""

# 1. frontend 빌드 (desktop/electron-builder.yml이 frontend/dist를 참조)
echo "   [1/3] Frontend 빌드 중..."
if [ -f "$PROJECT_ROOT/frontend/package.json" ]; then
    cd "$PROJECT_ROOT/frontend"
    npm install --silent 2>/dev/null
    npm run build
    echo "   ✅ Frontend 빌드 완료"
else
    echo "   ⚠️  frontend/package.json 없음, 기존 빌드 사용"
fi

# 2. desktop 의존성 설치
echo "   [2/3] Desktop 의존성 확인 중..."
cd "$DESKTOP_DIR"
if [ ! -d "node_modules" ]; then
    npm install --silent
    echo "   ✅ 의존성 설치 완료"
else
    echo "   ✅ 의존성 이미 설치됨"
fi

# 3. electron-builder로 DMG 생성
echo "   [3/3] DMG 생성 중 (electron-builder)..."
npm run build

echo ""
echo "✅ DMG 생성 완료!"
echo "   출력 경로: $OUTPUT_DIR/"
echo ""

# 생성된 DMG 파일 목록 출력
for dmg in "$OUTPUT_DIR"/*.dmg; do
    if [ -f "$dmg" ]; then
        echo "   📀 $(basename "$dmg") ($(du -h "$dmg" | cut -f1))"
    fi
done
echo ""
