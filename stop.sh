#!/bin/bash

# ETF Weekly Report - 백엔드·프론트엔드 서버 중단
# 프로젝트 루트에서 실행: ./stop.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/scripts/stop-servers.sh"
