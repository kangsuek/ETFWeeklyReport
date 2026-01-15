# Archive - 삭제된 파일 백업

**백업 날짜**: 2026-01-10

## 백업된 파일

이 디렉토리에는 코드 정리 과정에서 제거된 파일들이 백업되어 있습니다.

### 1. `pyproject.toml`
- **원래 위치**: `backend/pyproject.toml`
- **제거 이유**: Poetry 설정 파일이지만 실제로는 `requirements.txt` 사용
- **파일 크기**: 1.2KB

### 2. `test_batch.py`
- **원래 위치**: `backend/test_batch.py`
- **제거 이유**: 일회성 테스트 스크립트, pytest로 대체됨
- **파일 크기**: 1.2KB

### 3. `backfill_data.py`
- **원래 위치**: `backend/backfill_data.py`
- **제거 이유**: API 엔드포인트로 대체됨 (`POST /api/data/backfill`)
- **파일 크기**: 616B

## 복구 방법

파일을 복구해야 하는 경우:

```bash
# 특정 파일 복구
cp archive/pyproject.toml backend/

# 모든 파일 복구
cp archive/*.py backend/
cp archive/pyproject.toml backend/
```

## 참고

- 이 백업은 안전을 위해 보관됩니다
- 30일 후에도 문제가 없으면 삭제 가능
- 자세한 분석 내용은 `docs/UNNECESSARY_CODE_ANALYSIS.md` 참조
