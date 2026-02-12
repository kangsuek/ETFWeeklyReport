#!/bin/bash
# ETF Weekly Report - macOS 앱 빌드 스크립트
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MACOS_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$MACOS_DIR")"

echo "=== ETF Weekly Report macOS App Build ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# 1. uv 확인
if ! command -v uv &> /dev/null; then
  echo "ERROR: uv가 설치되어 있지 않습니다."
  echo "설치: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

# 2. Node.js 확인
if ! command -v node &> /dev/null; then
  echo "ERROR: Node.js가 설치되어 있지 않습니다."
  exit 1
fi

# 3. 앱 아이콘 생성
echo ">>> 앱 아이콘 생성 중..."
cd "$MACOS_DIR"
npm run generate-icons
echo "앱 아이콘 생성 완료."
echo ""

# 4. 프론트엔드 빌드
echo ">>> 프론트엔드 빌드 중..."
cd "$PROJECT_ROOT/frontend"
npm install
ELECTRON_BUILD=1 VITE_API_BASE_URL=http://localhost:18000/api npm run build
echo "프론트엔드 빌드 완료."
echo ""

# 5. 백엔드 의존성 확인
echo ">>> 백엔드 의존성 확인 중..."
cd "$PROJECT_ROOT/backend"
uv sync 2>/dev/null || uv pip install -r requirements.txt
echo "백엔드 의존성 확인 완료."
echo ""

# 6. Electron 앱 빌드
echo ">>> Electron 앱 빌드 중..."
cd "$MACOS_DIR"
npm install
npm run build
echo ""

echo "=== 빌드 완료 ==="
echo "출력 위치: $MACOS_DIR/release/"
ls -la "$MACOS_DIR/release/" 2>/dev/null || echo "(release 디렉토리를 확인하세요)"
