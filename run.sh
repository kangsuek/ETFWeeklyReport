#!/bin/bash

# ETF Weekly Report - 실행 스크립트
# 백엔드와 프론트엔드를 함께 실행합니다.

# 현재 디렉토리 저장
PROJECT_ROOT=$(pwd)

# logs 폴더 생성
mkdir -p "$PROJECT_ROOT/logs"

# 스크립트 전체 출력을 logs/run.log에 저장 (동시에 화면에도 출력)
exec > >(tee "$PROJECT_ROOT/logs/run.log") 2>&1

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 ETF Weekly Report 시작..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ========================================
# 백엔드 설정
# ========================================
echo "📦 [1/5] 백엔드 의존성 설치 중..."
cd "$PROJECT_ROOT/backend"

# 가상환경 확인 및 활성화
if [ -d "venv" ]; then
    echo "   가상환경 활성화 중..."
    if source venv/bin/activate 2>/dev/null; then
        PYTHON_CMD=python
        PIP_CMD=pip
        echo "   ✅ 가상환경 활성화 완료"
    else
        echo "   ⚠️  가상환경 활성화 실패, 시스템 Python 사용"
        PYTHON_CMD=python3
        PIP_CMD=pip3
    fi
else
    echo "   ⚠️  가상환경이 없습니다. 시스템 Python 사용"
    PYTHON_CMD=python3
    PIP_CMD=pip3
fi

# Python 명령어 확인
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "   ❌ $PYTHON_CMD 명령어를 찾을 수 없습니다."
    exit 1
fi

# pip 업그레이드
echo "   pip 업그레이드 중..."
if ! $PIP_CMD install --upgrade pip --quiet > /dev/null 2>&1; then
    echo "   ⚠️  pip 업그레이드 중 경고 발생 (계속 진행)"
fi

# 의존성 설치
echo "   의존성 설치 중..."
# 첫 번째 시도: 조용히 설치 시도
if $PIP_CMD install --quiet --no-cache-dir -r requirements.txt > /dev/null 2>&1; then
    echo "   ✅ 의존성 설치 완료"
else
    echo "   ⚠️  일부 패키지 설치 실패, 상세 로그로 재시도 중..."
    if ! $PIP_CMD install --no-cache-dir -r requirements.txt; then
        echo "   ❌ 의존성 설치 실패. 로그를 확인하세요."
        exit 1
    fi
    echo "   ✅ 의존성 설치 완료 (재시도 성공)"
fi

# pydantic-core가 제대로 작동하는지 확인 (문제가 있을 때만 재설치)
if ! $PYTHON_CMD -c "import pydantic_core" 2>/dev/null; then
    echo "   ⚠️  pydantic-core 문제 감지, 재설치 중..."
    $PIP_CMD uninstall -y pydantic-core pydantic 2>/dev/null || true
    if ! $PIP_CMD install --quiet --no-cache-dir pydantic-core 2>/dev/null; then
        echo "   ⚠️  조용한 설치 실패, 상세 로그로 재시도..."
        $PIP_CMD install --no-cache-dir pydantic-core || exit 1
    fi
    if ! $PIP_CMD install --quiet --no-cache-dir pydantic==2.5.0 2>/dev/null; then
        echo "   ⚠️  pydantic 설치 실패, 상세 로그로 재시도..."
        $PIP_CMD install --no-cache-dir pydantic==2.5.0 || exit 1
    fi
    echo "   ✅ pydantic-core 재설치 완료"
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
    if ! $PYTHON_CMD -m app.database 2>&1; then
        echo "   ❌ 데이터베이스 초기화 실패"
        exit 1
    fi
    echo "   ✅ 데이터베이스 초기화 완료"
else
    echo "   ✅ 기존 데이터베이스 사용"
fi

# ========================================
# 백엔드 서버 시작
# ========================================
echo ""
echo "🔧 [3/5] 백엔드 서버 시작 중 (포트 8000)..."
$PYTHON_CMD -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo "   ✅ 백엔드 서버 시작 (PID: $BACKEND_PID)"
echo "   📝 로그: $PROJECT_ROOT/logs/backend.log"

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
    echo "   package-lock.json 발견, npm ci 실행 중..."
    if npm ci --silent > /dev/null 2>&1; then
        echo "   ✅ npm ci 완료"
    else
        echo "   ⚠️  npm ci 실패, npm install로 재시도 중..."
        if npm install --silent > /dev/null 2>&1; then
            echo "   ✅ npm install 완료"
        else
            echo "   ❌ npm install 실패. 로그를 확인하세요."
            exit 1
        fi
    fi
else
    echo "   package-lock.json 없음, npm install 실행 중..."
    if npm install --silent > /dev/null 2>&1; then
        echo "   ✅ npm install 완료"
    else
        echo "   ❌ npm install 실패. 로그를 확인하세요."
        exit 1
    fi
fi
echo "   ✅ 프론트엔드 의존성 설치 완료"

# ========================================
# 프론트엔드 서버 시작
# ========================================
echo ""
echo "🎨 [5/5] 프론트엔드 개발 서버 시작 중..."

# 환경 변수 설정 (로컬 개발용)
export VITE_API_BASE_URL=http://localhost:8000/api

# 프론트엔드 개발 서버 시작
npm run dev -- --host 0.0.0.0 --port 5173 > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "   ✅ 프론트엔드 개발 서버 시작 (PID: $FRONTEND_PID)"
echo "   📝 로그: $PROJECT_ROOT/logs/frontend.log"

cd "$PROJECT_ROOT"

# ========================================
# 완료 메시지
# ========================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 모든 서버 시작 완료!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 접속 정보:"
echo "   - 🔧 백엔드 API:      http://localhost:8000"
echo "   - 📖 API 문서:        http://localhost:8000/docs"
echo "   - 📖 API 문서(ReDoc): http://localhost:8000/redoc"
echo "   - 🌐 웹 애플리케이션:    http://localhost:5173"

echo ""
echo "💡 팁:"
echo "   - Ctrl+C로 서버 종료"
echo "   - 백엔드 로그: logs/backend.log"
echo "   - 프론트엔드 로그: logs/frontend.log"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 프로세스 대기 (서버 유지)
wait $BACKEND_PID $FRONTEND_PID

