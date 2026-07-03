# Development Guide

코드 스타일·명령어·테스트 정책의 정본은 [AGENTS.md](../AGENTS.md)와 [CLAUDE.md](../CLAUDE.md)입니다. 이 문서는 요약과 보충만 담습니다.

## Quick Reference

| 항목 | 규칙 |
|------|------|
| Python | PEP 8, 4-space indent, type hints·docstring 필수, I/O는 `async/await` |
| JS/React | ESLint, 2-space indent, 함수형 컴포넌트 + Hooks, PropTypes 필수 |
| 네이밍 | Python `snake_case` / JS `camelCase`, 클래스·컴포넌트 `PascalCase`, 상수 `UPPER_CASE` |
| 커밋 타입 | `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore` |
| 테스트 | Given-When-Then 패턴, 커버리지 목표: 백엔드 80% / 프론트 70% / Critical Path 100% |

## 성능 원칙

- **Backend**: 블로킹 스크레이핑은 `asyncio.to_thread()`로 감싸기, DB 인덱스 활용, 배치 API로 N+1 방지
- **Frontend**: `React.memo`·`useMemo`로 불필요한 리렌더 방지, `React.lazy()` 코드 스플리팅

## 관련 문서

- [ARCHITECTURE.md](./ARCHITECTURE.md) — 프로젝트 구조
- [METRICS_SPEC.md](./METRICS_SPEC.md) — 지표 산식 (계산은 백엔드가 정본)
- [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) — 스키마 변경 시 갱신 필수
