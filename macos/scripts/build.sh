#!/bin/bash
# ETF Weekly Report - macOS 앱 빌드 스크립트
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MACOS_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$MACOS_DIR")"

# 앱에 번들할 uv 버전 (재현성을 위해 고정)
UV_VERSION="0.11.24"

echo "=== ETF Weekly Report macOS App Build ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# 1. uv 확인 (빌드 머신용 — 백엔드 의존성 검증에 사용)
if ! command -v uv &> /dev/null; then
  echo "ERROR: uv가 설치되어 있지 않습니다."
  echo "설치: curl -LsSf https://astral.sh/uv/install.sh | sh  또는  brew install uv"
  exit 1
fi

# 2. Node.js 확인
if ! command -v node &> /dev/null; then
  echo "ERROR: Node.js가 설치되어 있지 않습니다."
  exit 1
fi

# 3. macOS 앱 의존성 설치 (아이콘 생성에 필요한 sharp 포함 — 아이콘 생성보다 먼저!)
echo ">>> macOS 앱 의존성 설치 중..."
cd "$MACOS_DIR"
npm install
echo "macOS 앱 의존성 설치 완료."
echo ""

# 4. 앱 아이콘 생성 (이미 존재하면 스킵)
if [ -f "$MACOS_DIR/icons/icon.icns" ]; then
  echo ">>> 앱 아이콘이 이미 존재하여 생성을 건너뜁니다."
else
  echo ">>> 앱 아이콘 생성 중..."
  cd "$MACOS_DIR"
  npm run generate-icons
  echo "앱 아이콘 생성 완료."
fi
echo ""

# 5. 프론트엔드 빌드
echo ">>> 프론트엔드 빌드 중..."
cd "$PROJECT_ROOT/frontend"
npm install
ELECTRON_BUILD=1 VITE_API_BASE_URL=http://localhost:18000/api npm run build
echo "프론트엔드 빌드 완료."
echo ""

# 6. 백엔드 의존성 확인 (venv 생성 후 설치)
echo ">>> 백엔드 의존성 확인 중..."
cd "$PROJECT_ROOT/backend"
[ -d ".venv" ] || uv venv .venv
uv pip install -r requirements.txt --python .venv/bin/python
echo "백엔드 의존성 확인 완료."
echo ""

# 7. 번들용 uv 바이너리 다운로드 (resources/bin/uv-<arch>)
#    사용자 머신에 uv가 없어도 앱이 백엔드 환경을 구성할 수 있도록 함.
download_uv() {
  local arch="$1"          # arm64 | x64
  local triple dest
  case "$arch" in
    arm64) triple="aarch64-apple-darwin" ;;
    x64)   triple="x86_64-apple-darwin" ;;
    *) echo "ERROR: 알 수 없는 arch: $arch"; return 1 ;;
  esac
  dest="$MACOS_DIR/resources/bin/uv-$arch"
  mkdir -p "$(dirname "$dest")"
  if [ -f "$dest" ]; then
    echo "  uv($arch) 이미 존재: $dest"
    return 0
  fi
  local url="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${triple}.tar.gz"
  echo "  uv($arch) 다운로드: $url"
  local tmp
  tmp="$(mktemp -d)"
  curl -fsSL "$url" | tar -xz -C "$tmp"
  mv "$tmp/uv-${triple}/uv" "$dest"
  chmod +x "$dest"
  rm -rf "$tmp"
  echo "  uv($arch) → $dest"
}

# 아키텍처 선택: arm64, x64, 또는 universal (기본: universal)
ARCH="${1:-universal}"

echo ">>> 번들용 uv 바이너리 준비 중..."
case "$ARCH" in
  arm64) download_uv arm64 ;;
  x64)   download_uv x64 ;;
  universal|all) download_uv arm64; download_uv x64 ;;
  *) echo "ERROR: 지원하지 않는 아키텍처: $ARCH"; echo "사용법: $0 [arm64|x64|universal]"; exit 1 ;;
esac
echo ""

# 8. 코드 서명·공증 자격증명 감지
#    - Developer ID 인증서(CSC_LINK 또는 키체인)와 공증 자격증명이 있으면 서명+공증.
#    - 없으면 미서명 빌드(배포 시 Gatekeeper 경고 발생). 빌드는 정상 진행.
SIGN_ARGS=()
if [ -n "${APPLE_ID:-}" ] && [ -n "${APPLE_APP_SPECIFIC_PASSWORD:-}" ] && [ -n "${APPLE_TEAM_ID:-}" ]; then
  echo ">>> 서명·공증 자격증명 감지됨 → 서명 및 공증을 진행합니다 (team: $APPLE_TEAM_ID)"
  export APPLE_ID APPLE_APP_SPECIFIC_PASSWORD APPLE_TEAM_ID
  SIGN_ARGS=( --config.mac.notarize.teamId="$APPLE_TEAM_ID" )
else
  echo ">>> ⚠️  서명 자격증명 없음 → 미서명 빌드로 진행합니다."
  echo "    (배포하려면 APPLE_ID / APPLE_APP_SPECIFIC_PASSWORD / APPLE_TEAM_ID 와"
  echo "     Developer ID 인증서를 설정한 뒤 다시 빌드하세요.)"
  export CSC_IDENTITY_AUTO_DISCOVERY=false
fi
echo ""

# 9. Electron 앱 빌드
echo ">>> Electron 앱 빌드 중..."
cd "$MACOS_DIR"
case "$ARCH" in
  arm64)
    echo ">>> arm64 (Apple Silicon) DMG 빌드..."
    npx electron-builder --mac --arm64 "${SIGN_ARGS[@]+"${SIGN_ARGS[@]}"}"
    ;;
  x64)
    echo ">>> x64 (Intel) DMG 빌드..."
    npx electron-builder --mac --x64 "${SIGN_ARGS[@]+"${SIGN_ARGS[@]}"}"
    ;;
  universal|all)
    echo ">>> arm64 + x64 DMG 빌드..."
    npx electron-builder --mac --arm64 --x64 "${SIGN_ARGS[@]+"${SIGN_ARGS[@]}"}"
    ;;
esac
echo ""

echo "=== 빌드 완료 ==="
echo "출력 위치: $MACOS_DIR/release/"
ls -lh "$MACOS_DIR/release/"*.dmg 2>/dev/null || echo "(DMG 파일을 확인하세요)"
