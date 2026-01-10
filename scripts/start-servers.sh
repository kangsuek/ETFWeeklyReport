#!/bin/bash

# ETF Weekly Report - 개발 서버 시작 스크립트
# 백엔드(8000 포트)와 프론트엔드(5173 포트) 개발 서버를 시작합니다.

echo "🚀 개발 서버 시작 중..."
echo ""

# 프로젝트 루트 디렉토리 (스크립트가 scripts/ 폴더에 있으므로 상위 디렉토리로 이동)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# logs 폴더 생성
mkdir -p "$PROJECT_ROOT/logs"

# 백엔드 서버 시작
echo "  - 백엔드 서버 시작 중 (포트 8000)..."
cd "$PROJECT_ROOT/backend"

# 가상환경 활성화 및 서버 시작
if [ -d "venv" ]; then
  source venv/bin/activate
  python -m uvicorn app.main:app --reload --port 8000 > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
  BACKEND_PID=$!
  echo "    ✓ 백엔드 서버 시작 완료 (PID: $BACKEND_PID)"
  echo "    📝 로그: $PROJECT_ROOT/logs/backend.log"
else
  echo "    ❌ 가상환경을 찾을 수 없습니다. backend/venv 디렉토리를 확인하세요."
  exit 1
fi

# 백엔드 서버 시작 대기
sleep 2

# 프론트엔드 서버 시작
echo ""
echo "  - 프론트엔드 서버 시작 중 (포트 5173)..."
cd "$PROJECT_ROOT/frontend"

if [ -d "node_modules" ]; then
  npm run dev > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
  FRONTEND_PID=$!
  echo "    ✓ 프론트엔드 서버 시작 완료 (PID: $FRONTEND_PID)"
  echo "    📝 로그: $PROJECT_ROOT/logs/frontend.log"
else
  echo "    ❌ node_modules를 찾을 수 없습니다. 먼저 'npm install'을 실행하세요."
  exit 1
fi

# 서버 시작 대기
sleep 3

echo ""
echo "✅ 모든 개발 서버 시작 완료"
echo ""
echo "📊 서버 정보:"
echo "  - 백엔드:      http://localhost:8000"
echo "  - 프론트엔드:  http://localhost:5173 (또는 5174)"
echo "  - Swagger UI:  http://localhost:8000/docs"
echo ""
echo "💡 팁:"
echo "  - 프론트엔드 로그: tail -f logs/frontend.log"
echo "  - 서버 종료: ./scripts/stop-servers.sh"
echo "  - Ctrl+C로 로그 표시 중단 (서버는 계속 실행됨)"
echo ""
echo "📝 백엔드 로그 표시 중..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 백엔드 로그를 실시간으로 표시
tail -f "$PROJECT_ROOT/logs/backend.log"
