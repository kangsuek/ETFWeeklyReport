#!/bin/bash

# ETF Weekly Report - 개발 서버 종료 스크립트
# 백엔드(8000 포트)와 프론트엔드(5173/5174 포트) 개발 서버를 모두 종료합니다.

echo "🛑 개발 서버 종료 중..."

# 백엔드 서버 종료 (8000 포트)
echo "  - 백엔드 서버 종료 중 (포트 8000)..."
BACKEND_PIDS=$(lsof -ti:8000 2>/dev/null)
if [ -n "$BACKEND_PIDS" ]; then
  echo "$BACKEND_PIDS" | xargs kill -9 2>/dev/null
  echo "    ✓ 백엔드 서버 종료 완료"
else
  echo "    ℹ 백엔드 서버가 실행 중이지 않습니다"
fi

# 프론트엔드 서버 종료 (5173 포트)
echo "  - 프론트엔드 서버 종료 중 (포트 5173)..."
FRONTEND_PIDS_5173=$(lsof -ti:5173 2>/dev/null)
if [ -n "$FRONTEND_PIDS_5173" ]; then
  echo "$FRONTEND_PIDS_5173" | xargs kill -9 2>/dev/null
  echo "    ✓ 프론트엔드 서버 종료 완료 (5173)"
else
  echo "    ℹ 프론트엔드 서버가 실행 중이지 않습니다 (5173)"
fi

# 프론트엔드 서버 종료 (5174 포트 - 대체 포트)
echo "  - 프론트엔드 서버 종료 중 (포트 5174)..."
FRONTEND_PIDS_5174=$(lsof -ti:5174 2>/dev/null)
if [ -n "$FRONTEND_PIDS_5174" ]; then
  echo "$FRONTEND_PIDS_5174" | xargs kill -9 2>/dev/null
  echo "    ✓ 프론트엔드 서버 종료 완료 (5174)"
else
  echo "    ℹ 프론트엔드 서버가 실행 중이지 않습니다 (5174)"
fi

echo ""
echo "✅ 모든 개발 서버 종료 완료"
echo ""

# 실행 중인 포트 확인
echo "📊 현재 실행 중인 개발 서버 포트 확인:"
REMAINING_8000=$(lsof -ti:8000 2>/dev/null)
REMAINING_5173=$(lsof -ti:5173 2>/dev/null)
REMAINING_5174=$(lsof -ti:5174 2>/dev/null)

if [ -z "$REMAINING_8000" ] && [ -z "$REMAINING_5173" ] && [ -z "$REMAINING_5174" ]; then
  echo "  ✓ 모든 포트가 정리되었습니다"
else
  echo "  ⚠ 일부 포트가 여전히 사용 중입니다:"
  [ -n "$REMAINING_8000" ] && echo "    - 8000: 실행 중"
  [ -n "$REMAINING_5173" ] && echo "    - 5173: 실행 중"
  [ -n "$REMAINING_5174" ] && echo "    - 5174: 실행 중"
fi

echo ""
