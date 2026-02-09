#!/bin/bash
# ETF Weekly Report - macOS DMG 빌드 스크립트
#
# feature/macos-app 브랜치의 desktop 소스를 사용하여 DMG 파일을 생성합니다.
# 출력: desktop/release/*.dmg
#
# 사용법:
#   ./scripts/build-dmg.sh              # 현재 아키텍처용 빌드
#   ./scripts/build-dmg.sh --arm64      # Apple Silicon 전용
#   ./scripts/build-dmg.sh --x64        # Intel 전용
#   ./scripts/build-dmg.sh --universal  # 양쪽 모두 (arm64 + x64)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DESKTOP_DIR="$PROJECT_ROOT/desktop"
DESKTOP_BRANCH="feature/macos-app"

# 아키텍처 옵션 파싱
ARCH_FLAG=""
case "${1:-}" in
  --arm64)    ARCH_FLAG="--arm64" ;;
  --x64)      ARCH_FLAG="--x64" ;;
  --universal) ARCH_FLAG="" ;;  # electron-builder.yml 기본값 사용 (arm64 + x64)
  "")         ARCH_FLAG="" ;;
  *)
    echo "사용법: $0 [--arm64|--x64|--universal]"
    exit 1
    ;;
esac

echo "============================================"
echo "  ETF Weekly Report - DMG 빌드"
echo "============================================"
echo "프로젝트 루트: $PROJECT_ROOT"
echo "데스크톱 소스: $DESKTOP_BRANCH 브랜치"
[ -n "$ARCH_FLAG" ] && echo "아키텍처: $ARCH_FLAG" || echo "아키텍처: electron-builder.yml 설정 사용"
echo ""

# ─── 사전 조건 확인 ───────────────────────────────────────────────

echo ">>> [1/7] 사전 조건 확인..."

if ! command -v node &> /dev/null; then
  echo "ERROR: Node.js가 설치되어 있지 않습니다."
  exit 1
fi
echo "  Node.js $(node --version)"

if ! command -v npm &> /dev/null; then
  echo "ERROR: npm이 설치되어 있지 않습니다."
  exit 1
fi
echo "  npm $(npm --version)"

if ! command -v uv &> /dev/null; then
  echo "ERROR: uv가 설치되어 있지 않습니다."
  echo "  설치: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
echo "  uv $(uv --version)"

if ! command -v git &> /dev/null; then
  echo "ERROR: git이 설치되어 있지 않습니다."
  exit 1
fi

# feature/macos-app 브랜치 존재 확인
if ! git -C "$PROJECT_ROOT" rev-parse --verify "$DESKTOP_BRANCH" &> /dev/null; then
  echo "ERROR: '$DESKTOP_BRANCH' 브랜치가 존재하지 않습니다."
  echo "  git fetch origin $DESKTOP_BRANCH 를 실행해주세요."
  exit 1
fi

echo ""

# ─── desktop 소스 체크아웃 ─────────────────────────────────────────

echo ">>> [2/7] desktop 소스 체크아웃 ($DESKTOP_BRANCH)..."

# feature/macos-app 브랜치에서 desktop 관련 파일을 가져옴
cd "$PROJECT_ROOT"
git checkout "$DESKTOP_BRANCH" -- \
  desktop/main.js \
  desktop/preload.js \
  desktop/loading.html \
  desktop/loading.css \
  desktop/package.json \
  desktop/electron-builder.yml \
  desktop/scripts/ \
  desktop/icons/ \
  2>/dev/null || true

# 체크아웃된 파일 확인
if [ ! -f "$DESKTOP_DIR/package.json" ]; then
  echo "ERROR: desktop/package.json을 체크아웃할 수 없습니다."
  exit 1
fi

echo "  desktop 소스 준비 완료."
echo ""

# ─── 앱 아이콘 생성 ────────────────────────────────────────────────

echo ">>> [3/7] 앱 아이콘 생성..."
cd "$DESKTOP_DIR"
npm install --ignore-scripts 2>/dev/null
if [ -f "$DESKTOP_DIR/scripts/generate-icons.js" ]; then
  npm run generate-icons 2>/dev/null || echo "  아이콘 생성 스킵 (기존 아이콘 사용)"
else
  echo "  아이콘 생성 스크립트 없음 (기존 아이콘 사용)"
fi
echo ""

# ─── 프론트엔드 빌드 ───────────────────────────────────────────────

echo ">>> [4/7] 프론트엔드 빌드..."
cd "$PROJECT_ROOT/frontend"
npm install
ELECTRON_BUILD=1 VITE_API_BASE_URL=http://localhost:18000/api npm run build
echo "  프론트엔드 빌드 완료: frontend/dist/"
echo ""

# ─── 백엔드 의존성 확인 ────────────────────────────────────────────

echo ">>> [5/7] 백엔드 의존성 확인..."
cd "$PROJECT_ROOT/backend"
uv sync 2>/dev/null || uv pip install -r requirements.txt 2>/dev/null || true
echo "  백엔드 의존성 확인 완료."
echo ""

# ─── Electron 의존성 설치 ──────────────────────────────────────────

echo ">>> [6/7] Electron 의존성 설치..."
cd "$DESKTOP_DIR"
npm install
echo ""

# ─── DMG 빌드 ──────────────────────────────────────────────────────

echo ">>> [7/7] DMG 빌드 중..."
cd "$DESKTOP_DIR"

if [ -n "$ARCH_FLAG" ]; then
  npx electron-builder --mac dmg $ARCH_FLAG
else
  npx electron-builder --mac dmg
fi

echo ""
echo "============================================"
echo "  빌드 완료!"
echo "============================================"
echo ""
echo "출력 위치: $DESKTOP_DIR/release/"
echo ""
ls -lh "$DESKTOP_DIR/release/"*.dmg 2>/dev/null || echo "(DMG 파일을 찾을 수 없습니다)"
