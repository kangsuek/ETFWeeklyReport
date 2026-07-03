#!/bin/bash

# ETF Weekly Report - 전체 종료 스크립트
# 백엔드(uvicorn)·프론트엔드(vite/npm)와 관련 orphan 프로세스를 모두 종료합니다.
# 포트 기반 + 프로젝트 경로 기반으로 중복/좀비 프로세스까지 정리합니다.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🛑 ETF Weekly Report 전체 종료"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 자기 자신(이 스크립트) PID는 종료 대상에서 제외
SELF_PID=$$

# ────────────────────────────────────────────────
# 1) 포트 기반 종료
#    8000: 웹 백엔드 / 5173~5175: 프론트 dev(중복 대체 포트 포함) / 18000: Mac·Win 앱 백엔드
# ────────────────────────────────────────────────
PORTS="8000 5173 5174 5175 18000"
for PORT in $PORTS; do
  PIDS=$(lsof -ti tcp:$PORT 2>/dev/null | grep -v "^${SELF_PID}$")
  if [ -n "$PIDS" ]; then
    echo "  - 포트 $PORT 종료: $(echo $PIDS | tr '\n' ' ')"
    echo "$PIDS" | xargs kill -9 2>/dev/null
  else
    echo "  - 포트 $PORT: 실행 중 아님"
  fi
done

# ────────────────────────────────────────────────
# 2) 프로젝트 경로 기반 orphan 종료
#    포트를 잡지 않은 잔여 프로세스(vite/esbuild/npm/uvicorn/uv)를 이 프로젝트 범위에서만 정리
# ────────────────────────────────────────────────
echo "  - orphan 프로세스 정리..."
PATTERNS=(
  "${PROJECT_ROOT}/frontend/node_modules"   # vite, esbuild 등 프론트 자식 프로세스
  "${PROJECT_ROOT}/backend"                 # uv/uvicorn (venv 인터프리터 경로 포함)
  "uvicorn app.main:app"                    # 백엔드 서버(경로 미포함 케이스 대비)
)
for PAT in "${PATTERNS[@]}"; do
  # pgrep는 자기 자신/이 파이프라인을 매칭하지 않음. self PID는 추가로 제외.
  PIDS=$(pgrep -f "$PAT" 2>/dev/null | grep -v "^${SELF_PID}$")
  if [ -n "$PIDS" ]; then
    echo "    · '$PAT' → $(echo $PIDS | tr '\n' ' ')"
    echo "$PIDS" | xargs kill -9 2>/dev/null
  fi
done

# npm run dev 부모 프로세스(이 프로젝트에서 기동된 것) 정리
NPM_PIDS=$(pgrep -f "npm run dev" 2>/dev/null | grep -v "^${SELF_PID}$")
if [ -n "$NPM_PIDS" ]; then
  echo "    · 'npm run dev' → $(echo $NPM_PIDS | tr '\n' ' ')"
  echo "$NPM_PIDS" | xargs kill -9 2>/dev/null
fi

sleep 1

# ────────────────────────────────────────────────
# 3) 최종 확인
# ────────────────────────────────────────────────
echo ""
echo "📊 종료 후 포트 상태:"
REMAINING=""
for PORT in $PORTS; do
  P=$(lsof -ti tcp:$PORT 2>/dev/null | grep -v "^${SELF_PID}$")
  if [ -n "$P" ]; then
    echo "  ⚠ 포트 $PORT: 여전히 사용 중 ($(echo $P | tr '\n' ' '))"
    REMAINING="yes"
  fi
done
if [ -z "$REMAINING" ]; then
  echo "  ✓ 모든 포트가 정리되었습니다"
fi
echo ""
echo "✅ 종료 완료"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
