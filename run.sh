#!/bin/bash

# ETF Weekly Report - 프로그램 실행 스크립트
# 백엔드와 프론트엔드를 동시에 실행합니다.

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 프로젝트 루트 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}🚀 ETF Weekly Report 프로그램 실행${NC}"
echo ""

# 백엔드 프로세스 종료 함수
cleanup_backend() {
    if [ ! -z "$BACKEND_PID" ]; then
        echo -e "\n${YELLOW}백엔드 프로세스 종료 중...${NC}"
        kill $BACKEND_PID 2>/dev/null || true
        wait $BACKEND_PID 2>/dev/null || true
    fi
}

# 프론트엔드 프로세스 종료 함수
cleanup_frontend() {
    if [ ! -z "$FRONTEND_PID" ]; then
        echo -e "\n${YELLOW}프론트엔드 프로세스 종료 중...${NC}"
        kill $FRONTEND_PID 2>/dev/null || true
        wait $FRONTEND_PID 2>/dev/null || true
    fi
}

# 종료 시 정리
cleanup() {
    cleanup_backend
    cleanup_frontend
    exit 0
}

# 시그널 핸들러 등록
trap cleanup SIGINT SIGTERM

# 백엔드 실행 함수
start_backend() {
    echo -e "${GREEN}📦 백엔드 실행 중...${NC}"
    
    cd backend
    
    # 가상환경 확인 및 생성
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}가상환경이 없습니다. 생성 중...${NC}"
        python3 -m venv venv
    fi
    
    # 가상환경 활성화
    source venv/bin/activate
    
    # 의존성 설치 확인
    if [ ! -f "venv/.installed" ]; then
        echo -e "${YELLOW}의존성 설치 중...${NC}"
        pip install -q -r requirements.txt
        touch venv/.installed
    fi
    
    # 데이터베이스 초기화 확인
    if [ ! -d "data" ]; then
        mkdir -p data
    fi
    
    echo -e "${GREEN}백엔드 서버 시작: http://localhost:8000${NC}"
    echo -e "${GREEN}API 문서: http://localhost:8000/docs${NC}"
    
    # 백엔드 실행 (백그라운드)
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
    BACKEND_PID=$!
    
    cd ..
    
    # 백엔드가 시작될 때까지 대기
    echo -n "백엔드 시작 대기 중"
    for i in {1..30}; do
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            echo -e "\n${GREEN}✅ 백엔드 실행 완료${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    
    echo -e "\n${RED}❌ 백엔드 시작 실패${NC}"
    return 1
}

# 프론트엔드 실행 함수
start_frontend() {
    echo -e "${GREEN}🎨 프론트엔드 실행 중...${NC}"
    
    cd frontend
    
    # node_modules 확인
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}의존성 설치 중...${NC}"
        npm install
    fi
    
    echo -e "${GREEN}프론트엔드 서버 시작: http://localhost:5173${NC}"
    
    # 프론트엔드 실행 (백그라운드)
    npm run dev > /dev/null 2>&1 &
    FRONTEND_PID=$!
    
    cd ..
    
    # 프론트엔드가 시작될 때까지 대기
    echo -n "프론트엔드 시작 대기 중"
    for i in {1..30}; do
        if curl -s http://localhost:5173 > /dev/null 2>&1; then
            echo -e "\n${GREEN}✅ 프론트엔드 실행 완료${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    
    echo -e "\n${YELLOW}⚠️  프론트엔드 시작 확인 실패 (수동으로 확인해주세요)${NC}"
    return 0
}

# 메인 실행
main() {
    # 기존 프로세스 확인 및 종료
    if lsof -ti:8000 > /dev/null 2>&1; then
        echo -e "${YELLOW}포트 8000이 이미 사용 중입니다. 기존 프로세스를 종료합니다.${NC}"
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
    
    if lsof -ti:5173 > /dev/null 2>&1; then
        echo -e "${YELLOW}포트 5173이 이미 사용 중입니다. 기존 프로세스를 종료합니다.${NC}"
        lsof -ti:5173 | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
    
    # 백엔드 시작
    if ! start_backend; then
        cleanup
        exit 1
    fi
    
    sleep 1
    
    # 프론트엔드 시작
    if ! start_frontend; then
        cleanup
        exit 1
    fi
    
    echo ""
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ 모든 서버가 실행되었습니다!${NC}"
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BLUE}📱 프론트엔드:${NC} http://localhost:5173"
    echo -e "${BLUE}🔧 백엔드 API:${NC} http://localhost:8000"
    echo -e "${BLUE}📚 API 문서:${NC} http://localhost:8000/docs"
    echo ""
    echo -e "${YELLOW}종료하려면 Ctrl+C를 누르세요.${NC}"
    echo ""
    
    # 프로세스가 종료될 때까지 대기
    wait
}

# 스크립트 실행
main

