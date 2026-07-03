# 개선 백로그 (완료 아카이브)

> **분석일:** 2026-07-03 · **브랜치:** `feature/macos-app` · **상태:** 전 항목 완료 (2026-07-03)
> 상세 작업 내용은 각 커밋 메시지 참조. 새 개선 항목은 이 문서에 추가.

## 완료 내역

| 항목 | 내용 | 비고 |
|---|---|---|
| P1-1.1 | 블로킹 스크레이핑 `asyncio.to_thread` 래핑 | GET /news/{ticker} 온디맨드 경로 포함 |
| P1-1.2 | X-No-Cache 전체 삭제 → 티커 단위 무효화 | 티커 없으면 전체 삭제 폴백 |
| P1-1.3 | `on_event` → lifespan 전환 | shutdown에서 `close_connection_pool()` 호출 |
| P1-1.4 | 라우터의 `sqlite3.Error` 직접 catch 제거 | `DatabaseException`으로 변환 |
| P1-1.5 | DB 방향 확정: **SQLite 전용** | placeholder 잔재 제거 |
| P2-2.1 | Perplexity API 호출부 데드코드 삭제 (~250줄) | 프롬프트 생성만 유지, settings 키 플러밍 제거 |
| P2-2.2~2.4 | 함수/import/상수 데드코드 삭제 | |
| P2-2.5 | 미소비 엔드포인트 3개 제거 | collect-fundamentals ×2, cache/clear. 문서·SDK 재생성 |
| P3-3.1 | 지표 계산 백엔드 일원화 | `metrics_service.py` 신설(정본), [METRICS_SPEC.md](./METRICS_SPEC.md) 명세. 차트 RSI/MACD 라인만 프론트 계산 유지 |
| P3-3.2 | 포맷터 이중화 해소 | formatters.js → format.js 흡수 |
| P3-3.3 | 거대 파일 분리 | data_collector 3분할, etfs 라우터 서비스 위임, ETFDetail 섹션 추출, api_keys 라우터 분리 |
| P3-3.4 | CACHE_TTL 중복 → config.py, 단일 프로세스 제약 문서화 | |
| P4 | 문서 불일치 현행화 | CLAUDE.md·BRANCHES.md·API 문서 |

## 작업 시 주의사항 (재분석할 때 유효)

1. **브랜치:** `main`은 병렬 fork — 여기서 찾은 항목이 main에도 있다고 가정하지 말 것. 기계적 merge/sync 금지 ([BRANCHES.md](./BRANCHES.md)).
2. **테스트:** `backend/`에서 `uv run pytest` (conftest.py가 임시 DB로 격리). `pip`/`python` 직접 호출 금지.
3. **삭제 전 재검증:** grep으로 0 참조 확인 후 삭제.
4. **완료 판정:** 백엔드 `uv run pytest` + `uv run flake8 app/`, 프론트 `npm test && npm run lint && npm run build` 통과. 엔드포인트 삭제 시 [API_SPECIFICATION.md](./API_SPECIFICATION.md) 갱신 + `bash sdk/generate.sh`.
