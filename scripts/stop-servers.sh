#!/bin/bash

# ETF Weekly Report - 개발 서버 종료 스크립트
# 백엔드(8000 포트)와 프론트엔드(5173/5174 포트) 개발 서버를 모두 종료합니다.

echo "🛑 개발 서버 종료 중..."

graceful_kill() {
  local port=$1
  local label=$2
  local pids
  pids=$(lsof -ti:"$port" 2>/dev/null)
  if [ -z "$pids" ]; then
    echo "    ℹ $label 서버가 실행 중이지 않습니다 (포트 $port)"
    return
  fi

  echo "$pids" | xargs kill -15 2>/dev/null
  local waited=0
  while [ $waited -lt 5 ]; do
    remaining=$(lsof -ti:"$port" 2>/dev/null)
    [ -z "$remaining" ] && break
    sleep 1
    waited=$((waited + 1))
  done

  remaining=$(lsof -ti:"$port" 2>/dev/null)
  if [ -n "$remaining" ]; then
    echo "$remaining" | xargs kill -9 2>/dev/null
    echo "    ✓ $label 서버 강제 종료 (포트 $port)"
  else
    echo "    ✓ $label 서버 정상 종료 (포트 $port)"
  fi
}

graceful_kill 8000 "백엔드"
graceful_kill 5173 "프론트엔드"
graceful_kill 5174 "프론트엔드(대체)"

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
