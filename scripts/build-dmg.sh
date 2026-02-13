#!/bin/bash
# ETF Weekly Report - 데스크톱 앱 빌드 스크립트
#
# macOS DMG 및 Windows EXE(NSIS) 인스톨러를 생성합니다.
# - DMG: feature/macos-app 브랜치의 macos/ 소스 사용
# - EXE: feature/windows-app 브랜치의 windows/ 소스 사용
#
# 사용법:
#   ./scripts/build-dmg.sh                    # DMG + EXE 모두 빌드
#   ./scripts/build-dmg.sh --mac              # DMG만 빌드
#   ./scripts/build-dmg.sh --win              # EXE만 빌드
#   ./scripts/build-dmg.sh --mac --arm64      # DMG (Apple Silicon만)
#   ./scripts/build-dmg.sh --mac --x64        # DMG (Intel만)
#   ./scripts/build-dmg.sh --mac --universal  # DMG (arm64 + x64)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ─── 브랜치·디렉터리 설정 ─────────────────────────────────────────
MACOS_APP_BRANCH="feature/macos-app"
WINDOWS_APP_BRANCH="feature/windows-app"
MACOS_APP_SOURCE_DIR="${MACOS_APP_SOURCE_DIR:-$PROJECT_ROOT/macos}"
WINDOWS_APP_SOURCE_DIR="${WINDOWS_APP_SOURCE_DIR:-$PROJECT_ROOT/windows}"

# ─── 옵션 파싱 ───────────────────────────────────────────────────
BUILD_MAC=false
BUILD_WIN=false
ARCH_FLAG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mac)      BUILD_MAC=true; shift ;;
    --win)      BUILD_WIN=true; shift ;;
    --arm64)    ARCH_FLAG="--arm64"; shift ;;
    --x64)      ARCH_FLAG="--x64"; shift ;;
    --universal) ARCH_FLAG=""; shift ;;
    -h|--help)
      echo "사용법: $0 [--mac] [--win] [--arm64|--x64|--universal]"
      echo ""
      echo "  --mac        macOS DMG만 빌드"
      echo "  --win        Windows EXE만 빌드"
      echo "  (생략)       DMG + EXE 모두 빌드"
      echo ""
      echo "  --arm64      Apple Silicon 전용 (macOS)"
      echo "  --x64        Intel 전용 (macOS)"
      echo "  --universal  양쪽 모두 (macOS, 기본값)"
      exit 0
      ;;
    *)
      echo "ERROR: 알 수 없는 옵션: $1"
      echo "사용법: $0 [--mac] [--win] [--arm64|--x64|--universal]"
      exit 1
      ;;
  esac
done

# 둘 다 지정하지 않으면 모두 빌드
if ! $BUILD_MAC && ! $BUILD_WIN; then
  BUILD_MAC=true
  BUILD_WIN=true
fi

# ─── 헤더 출력 ───────────────────────────────────────────────────

echo "============================================"
echo "  ETF Weekly Report - 데스크톱 앱 빌드"
echo "============================================"
echo "프로젝트 루트: $PROJECT_ROOT"
$BUILD_MAC && echo "  [O] macOS DMG  (브랜치: $MACOS_APP_BRANCH)" || echo "  [ ] macOS DMG  (건너뜀)"
$BUILD_WIN && echo "  [O] Windows EXE (브랜치: $WINDOWS_APP_BRANCH)" || echo "  [ ] Windows EXE (건너뜀)"
[ -n "$ARCH_FLAG" ] && echo "  아키텍처: $ARCH_FLAG" || echo "  아키텍처: 기본값"
echo ""

# ─── [1] 사전 조건 확인 ──────────────────────────────────────────

echo ">>> [1] 사전 조건 확인..."

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

# 브랜치 존재 확인
if $BUILD_MAC; then
  if ! git -C "$PROJECT_ROOT" rev-parse --verify "$MACOS_APP_BRANCH" &> /dev/null; then
    echo "ERROR: '$MACOS_APP_BRANCH' 브랜치가 존재하지 않습니다."
    echo "  git fetch origin $MACOS_APP_BRANCH 를 실행해주세요."
    exit 1
  fi
fi

if $BUILD_WIN; then
  if ! git -C "$PROJECT_ROOT" rev-parse --verify "$WINDOWS_APP_BRANCH" &> /dev/null; then
    echo "ERROR: '$WINDOWS_APP_BRANCH' 브랜치가 존재하지 않습니다."
    echo "  git fetch origin $WINDOWS_APP_BRANCH 를 실행해주세요."
    exit 1
  fi
fi

echo ""

# ─── [2] 앱 소스 체크아웃 ────────────────────────────────────────

echo ">>> [2] 앱 소스 체크아웃..."
cd "$PROJECT_ROOT"

if $BUILD_MAC; then
  echo "  macOS 소스 ($MACOS_APP_BRANCH)..."
  git checkout "$MACOS_APP_BRANCH" -- \
    macos/main.js \
    macos/preload.js \
    macos/loading.html \
    macos/loading.css \
    macos/package.json \
    macos/electron-builder.yml \
    macos/scripts/ \
    macos/icons/ \
    2>/dev/null || true

  if [ ! -f "$MACOS_APP_SOURCE_DIR/package.json" ]; then
    echo "ERROR: Mac 앱 package.json을 체크아웃할 수 없습니다."
    exit 1
  fi
  echo "    Mac 앱 소스 준비 완료."
fi

if $BUILD_WIN; then
  echo "  Windows 소스 ($WINDOWS_APP_BRANCH)..."
  git checkout "$WINDOWS_APP_BRANCH" -- \
    windows/main.js \
    windows/preload.js \
    windows/loading.html \
    windows/loading.css \
    windows/package.json \
    windows/electron-builder.yml \
    windows/scripts/ \
    windows/icons/ \
    2>/dev/null || true

  if [ ! -f "$WINDOWS_APP_SOURCE_DIR/package.json" ]; then
    echo "ERROR: Windows 앱 package.json을 체크아웃할 수 없습니다."
    exit 1
  fi
  echo "    Windows 앱 소스 준비 완료."
fi

echo ""

# ─── [3] 앱 아이콘 생성 ──────────────────────────────────────────

echo ">>> [3] 앱 아이콘 생성..."

if $BUILD_MAC; then
  echo "  macOS 아이콘..."
  cd "$MACOS_APP_SOURCE_DIR"
  npm install --ignore-scripts 2>/dev/null
  if [ -f "$MACOS_APP_SOURCE_DIR/scripts/generate-icons.js" ]; then
    npm run generate-icons 2>/dev/null || echo "    아이콘 생성 스킵 (기존 아이콘 사용)"
  else
    echo "    아이콘 생성 스크립트 없음 (기존 아이콘 사용)"
  fi
fi

if $BUILD_WIN; then
  echo "  Windows 아이콘..."
  cd "$WINDOWS_APP_SOURCE_DIR"
  npm install --ignore-scripts 2>/dev/null
  if [ -f "$WINDOWS_APP_SOURCE_DIR/scripts/generate-icons.js" ]; then
    npm run generate-icons 2>/dev/null || echo "    아이콘 생성 스킵 (기존 아이콘 사용)"
  else
    echo "    아이콘 생성 스크립트 없음 (기존 아이콘 사용)"
  fi
fi

echo ""

# ─── [4] 프론트엔드 빌드 ─────────────────────────────────────────

echo ">>> [4] 프론트엔드 빌드..."
cd "$PROJECT_ROOT/frontend"
npm install
ELECTRON_BUILD=1 VITE_API_BASE_URL=http://localhost:18000/api npm run build
echo "  프론트엔드 빌드 완료: frontend/dist/"
echo ""

# ─── [5] 백엔드 의존성 확인 ──────────────────────────────────────

echo ">>> [5] 백엔드 의존성 확인..."
cd "$PROJECT_ROOT/backend"
uv sync 2>/dev/null || uv pip install -r requirements.txt 2>/dev/null || true
echo "  백엔드 의존성 확인 완료."
echo ""

# ─── [6] Electron 의존성 설치 ────────────────────────────────────

echo ">>> [6] Electron 의존성 설치..."

if $BUILD_MAC; then
  echo "  macOS Electron 의존성..."
  cd "$MACOS_APP_SOURCE_DIR"
  npm install
fi

if $BUILD_WIN; then
  echo "  Windows Electron 의존성..."
  cd "$WINDOWS_APP_SOURCE_DIR"
  npm install
fi

echo ""

# ─── [7] 빌드 실행 ───────────────────────────────────────────────

STEP=7

if $BUILD_MAC; then
  echo ">>> [$STEP] macOS DMG 빌드 중..."
  cd "$MACOS_APP_SOURCE_DIR"

  if [ -n "$ARCH_FLAG" ]; then
    npx electron-builder --mac dmg $ARCH_FLAG
  else
    npx electron-builder --mac dmg
  fi

  echo "  macOS DMG 빌드 완료."
  echo ""
  STEP=$((STEP + 1))
fi

if $BUILD_WIN; then
  echo ">>> [$STEP] Windows EXE 빌드 중..."
  cd "$WINDOWS_APP_SOURCE_DIR"

  npx electron-builder --win nsis --x64

  echo "  Windows EXE 빌드 완료."
  echo ""
fi

# ─── 결과 출력 ────────────────────────────────────────────────────

echo "============================================"
echo "  빌드 완료!"
echo "============================================"
echo ""

if $BUILD_MAC; then
  echo "[macOS DMG]"
  echo "  출력 위치: $MACOS_APP_SOURCE_DIR/release/"
  ls -lh "$MACOS_APP_SOURCE_DIR/release/"*.dmg 2>/dev/null || echo "  (DMG 파일을 찾을 수 없습니다)"
  echo ""
fi

if $BUILD_WIN; then
  echo "[Windows EXE]"
  echo "  출력 위치: $WINDOWS_APP_SOURCE_DIR/release/"
  ls -lh "$WINDOWS_APP_SOURCE_DIR/release/"*.exe 2>/dev/null || echo "  (EXE 파일을 찾을 수 없습니다)"
  echo ""
fi
