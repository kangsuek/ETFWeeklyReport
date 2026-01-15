#!/bin/bash
# Render.com 배포를 위한 시작 스크립트

# 데이터베이스 초기화
python -m app.database

# 서버 시작
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
