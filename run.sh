#!/bin/bash

# ETF Weekly Report - Replit 실행 스크립트
# 백엔드와 프론트엔드를 함께 실행합니다.

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 ETF Weekly Report 시작..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 현재 디렉토리 저장
PROJECT_ROOT=$(pwd)

# ========================================
# 백엔드 설정
# ========================================
echo "📦 [1/5] 백엔드 의존성 설치 중..."
cd "$PROJECT_ROOT/backend"

# pip 업그레이드
pip install --upgrade pip --quiet 2>/dev/null

# 의존성 설치
pip install -r requirements.txt --quiet 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  일부 패키지 설치 실패, 기본 패키지로 계속 진행..."
fi

echo "   ✅ 백엔드 의존성 설치 완료"

# ========================================
# 데이터베이스 초기화
# ========================================
echo ""
echo "🗃️  [2/5] 데이터베이스 확인 중..."

if [ ! -f "data/etf_data.db" ]; then
    echo "   새 데이터베이스 생성 중..."
    mkdir -p data
    python -m app.database
    echo "   ✅ 데이터베이스 초기화 완료"
else
    echo "   ✅ 기존 데이터베이스 사용"
fi

# ========================================
# 백엔드 서버 시작
# ========================================
echo ""
echo "🔧 [3/5] 백엔드 서버 시작 중 (포트 8000)..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "   ✅ 백엔드 서버 시작 (PID: $BACKEND_PID)"

# 백엔드 시작 대기
sleep 3

# ========================================
# 프론트엔드 설정
# ========================================
echo ""
echo "📦 [4/5] 프론트엔드 의존성 설치 중..."
cd "$PROJECT_ROOT/frontend"

# package-lock.json이 있으면 ci 사용, 없으면 install
if [ -f "package-lock.json" ]; then
    npm ci --silent 2>/dev/null || npm install --silent
else
    npm install --silent
fi
echo "   ✅ 프론트엔드 의존성 설치 완료"

# ========================================
# 프론트엔드 빌드 및 서버 시작
# ========================================
echo ""
echo "🎨 [5/5] 프론트엔드 빌드 및 서버 시작 중..."

# 프로덕션 빌드
npm run build --silent 2>/dev/null

# 프론트엔드 서버 시작 (preview 모드)
npm run preview -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!
echo "   ✅ 프론트엔드 서버 시작 (PID: $FRONTEND_PID)"

cd "$PROJECT_ROOT"

# ========================================
# 완료 메시지
# ========================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 모든 서버 시작 완료!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 서버 정보:"
echo "   - 🌐 웹 애플리케이션: https://$REPL_SLUG.$REPL_OWNER.repl.co"
echo "   - 🔧 백엔드 API:      http://localhost:8000"
echo "   - 📖 API 문서:        http://localhost:8000/docs"
echo ""
echo "💡 팁:"
echo "   - Ctrl+C로 서버 종료"
echo "   - 새 탭에서 Shell 열어서 추가 명령 실행 가능"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 프로세스 대기 (서버 유지)
wait $BACKEND_PID $FRONTEND_PID

