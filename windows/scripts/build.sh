#!/bin/bash
# ETF Weekly Report - Windows 앱 빌드 스크립트
# WSL 또는 Git Bash에서 실행
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WINDOWS_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$WINDOWS_DIR")"

echo "=== ETF Weekly Report Windows App Build ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# 1. uv 확인
if ! command -v uv &> /dev/null; then
  echo "ERROR: uv가 설치되어 있지 않습니다."
  echo "설치: powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\""
  exit 1
fi

# 2. Node.js 확인
if ! command -v node &> /dev/null; then
  echo "ERROR: Node.js가 설치되어 있지 않습니다."
  exit 1
fi

# 3. 앱 아이콘 생성
echo ">>> 앱 아이콘 생성 중..."
cd "$WINDOWS_DIR"
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
cd "$WINDOWS_DIR"
npm install

echo ">>> x64 Windows NSIS 인스톨러 빌드..."
npx electron-builder --win --x64
echo ""

echo "=== 빌드 완료 ==="
echo "출력 위치: $WINDOWS_DIR/release/"
ls -lh "$WINDOWS_DIR/release/"*.exe 2>/dev/null || echo "(EXE 파일을 확인하세요)"
