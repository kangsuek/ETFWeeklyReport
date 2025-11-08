# 🔬 서브프로젝트 작업 지시서: 네이버 뉴스 API 실시간 스크래핑 구현

## 📌 작업 배경

### 프로젝트 개요
- **메인 프로젝트**: ETF 주간 리포트 자동화 시스템
- **현재 상황**: Phase 2 - Step 4에서 뉴스 스크래핑을 **Mock 데이터**로 구현
- **문제점**: Mock 구현으로는 실시간 뉴스 수집 불가
- **초기 계획**: Selenium/Playwright 사용 예정이었음
- **변경 사항**: 네이버 공식 검색 API 사용으로 변경 (더 안정적이고 간단함)

### 왜 서브프로젝트인가?
1. **기술적 불확실성 검증**: API로 실제 뉴스 수집이 가능한지 먼저 확인
2. **메인 코드와 분리**: 프로토타입 성공 시 메인 코드에 통합
3. **리스크 관리**: 실패 시 대안 검토 (RSS, 다른 API 등)

---

## 🎯 서브프로젝트 목표

### 최종 목표
네이버 검색 API를 사용하여 6개 종목(ETF 4개 + 주식 2개)에 대한 실시간 뉴스를 안정적으로 수집할 수 있는지 검증

### 단계별 목표

#### ✅ 1단계 (이번 작업): 기본 API 호출 구현 (1시간)
- 네이버 뉴스 API 기본 호출 성공
- 단일 키워드로 10개 뉴스 수집
- HTML 태그 제거 및 날짜 파싱
- 결과 검증 및 문서화

#### ⏳ 2단계 (다음 작업): 다중 키워드 및 필터링 (1시간)
- 6개 종목별 키워드로 테스트
- 날짜 범위 필터링
- 관련도 점수 계산
- Rate Limiting 구현

#### ⏳ 3단계 (최종): 메인 코드 통합 (1시간)
- `app/services/news_scraper.py` 수정
- Mock 코드 제거
- 테스트 수정 및 실행
- 문서 업데이트

---

## 📋 1단계 작업 지시 (이번 세션)

### 작업 위치
```
작업 디렉토리: /Users/kangsuek/pythonProject/ETFWeeklyReport/backend/prototypes/news_scraper_poc/
```

### 이미 생성된 파일 (참고용)
- ✅ `README.md`: 프로젝트 개요 및 API 스펙
- ✅ `STEP1_PLAN.md`: 1단계 세부 작업 계획 (5개 Task)
- ✅ `WORK_INSTRUCTION.md`: 현재 파일

### 생성해야 할 파일
1. `.env`: API 인증 정보
2. `requirements.txt`: Python 의존성
3. `naver_news_api.py`: 메인 스크립트
4. `test_basic.py`: 테스트 스크립트
5. `STEP1_RESULT.md`: 결과 문서

---

## 🔑 네이버 API 정보

### API 문서
- **공식 문서**: https://developers.naver.com/docs/serviceapi/search/news/news.md
- **엔드포인트**: `https://openapi.naver.com/v1/search/news.json`
- **메서드**: GET
- **일일 한도**: 25,000회 (무료)

### 인증 정보 (중요!)
```
Client ID: pQbDBJ1we0Cpv5l54xne
Client Secret: GcptomaJI1
```

**⚠️ 주의**: 이 정보는 `.env` 파일에 저장하고 `.gitignore`에 추가하세요!

### API 요청 형식
```python
import requests

url = "https://openapi.naver.com/v1/search/news.json"
headers = {
    "X-Naver-Client-Id": "pQbDBJ1we0Cpv5l54xne",
    "X-Naver-Client-Secret": "GcptomaJI1"
}
params = {
    "query": "AI",
    "display": 10,
    "start": 1,
    "sort": "date"
}

response = requests.get(url, headers=headers, params=params)
data = response.json()
```

### API 응답 형식
```json
{
  "lastBuildDate": "Mon, 08 Nov 2025 15:30:00 +0900",
  "total": 1234567,
  "start": 1,
  "display": 10,
  "items": [
    {
      "title": "국내 <b>AI</b> 기술 발전...",
      "originallink": "http://원본URL...",
      "link": "http://네이버뉴스URL...",
      "description": "<b>AI</b> 기술이 급속도로...",
      "pubDate": "Mon, 08 Nov 2025 14:50:00 +0900"
    }
  ]
}
```

### 주요 파라미터
| 파라미터 | 타입 | 필수 | 설명 | 기본값 | 범위 |
|---------|------|------|------|--------|------|
| query | String | Y | 검색어 (UTF-8) | - | - |
| display | Integer | N | 결과 개수 | 10 | 1-100 |
| start | Integer | N | 시작 위치 | 1 | 1-1000 |
| sort | String | N | 정렬 방식 | sim | sim(정확도), date(날짜) |

### 에러 코드
| 코드 | HTTP | 의미 | 대응 |
|------|------|------|------|
| SE01 | 400 | 잘못된 쿼리 | URL/파라미터 확인 |
| SE02 | 400 | 잘못된 display | 1-100 범위 확인 |
| SE03 | 400 | 잘못된 start | 1-1000 범위 확인 |
| SE06 | 400 | 인코딩 오류 | UTF-8 인코딩 확인 |
| 401 | 401 | 인증 실패 | Client ID/Secret 확인 |
| 403 | 403 | API 권한 없음 | 개발자 센터에서 검색 API 활성화 |
| 429 | 429 | Rate Limit | 일일 한도 25,000회 확인 |
| SE99 | 500 | 서버 오류 | 재시도 또는 개발자 포럼 신고 |

---

## 📝 1단계 세부 작업 (Task 1.1 ~ 1.5)

### Task 1.1: 프로토타입 환경 설정 (10분)

#### 체크리스트
- [ ] `.env` 파일 생성
  ```env
  NAVER_CLIENT_ID=pQbDBJ1we0Cpv5l54xne
  NAVER_CLIENT_SECRET=GcptomaJI1
  ```
- [ ] `.gitignore`에 `.env` 추가 (보안)
- [ ] `requirements.txt` 생성
  ```txt
  requests==2.31.0
  python-dotenv==1.0.0
  ```
- [ ] 패키지 설치: `pip install -r requirements.txt`

---

### Task 1.2: 기본 API 호출 스크립트 작성 (20분)

#### 파일: `naver_news_api.py`

**구현 내용:**
1. 환경 변수 로드 (`python-dotenv`)
2. `search_news()` 함수 구현
3. HTTP 요청 헤더 설정
4. JSON 응답 파싱
5. 에러 핸들링 (try-except)

**함수 시그니처:**
```python
def search_news(
    query: str,
    display: int = 10,
    start: int = 1,
    sort: str = "date"
) -> dict:
    """
    네이버 뉴스 검색 API 호출
    
    Args:
        query: 검색 키워드 (UTF-8)
        display: 검색 결과 개수 (1-100)
        start: 검색 시작 위치 (1-1000)
        sort: 정렬 방식 (sim: 정확도, date: 날짜)
    
    Returns:
        dict: API 응답 JSON
        
    Raises:
        requests.exceptions.RequestException: API 호출 실패
    """
```

**에러 핸들링:**
```python
try:
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()  # 4xx, 5xx 에러 발생
    return response.json()
except requests.exceptions.HTTPError as e:
    if response.status_code == 401:
        print("❌ 인증 실패: Client ID/Secret 확인")
    elif response.status_code == 403:
        print("❌ API 권한 없음: 개발자 센터에서 검색 API 활성화 필요")
    elif response.status_code == 429:
        print("❌ Rate Limit 초과: 일일 한도 25,000회 확인")
    else:
        print(f"❌ HTTP 에러: {e}")
    raise
except Exception as e:
    print(f"❌ 예상치 못한 오류: {e}")
    raise
```

---

### Task 1.3: 단일 키워드 테스트 (15분)

#### 파일: `test_basic.py`

**구현 내용:**
1. "AI" 키워드로 10개 뉴스 검색
2. 응답 필드 검증
3. 결과 출력 (표 형식)

**출력 예시:**
```
========================================
네이버 뉴스 API 테스트
========================================
검색 키워드: AI
검색 결과: 10건 / 전체 1,234,567건
응답 시간: 0.5초
========================================

[1] 제목: 국내 AI 기술 발전...
    URL: https://news.naver.com/...
    원본 URL: https://...
    날짜: Mon, 08 Nov 2025 14:50:00 +0900
    출처: (description에서 추출)
    요약: AI 기술이 급속도로...
    
[2] ...
```

**검증 항목:**
- ✅ API 호출 성공 (HTTP 200)
- ✅ `items` 배열 존재
- ✅ 각 아이템에 `title`, `link`, `pubDate`, `description` 존재
- ✅ 결과 개수 = `display` 파라미터 값
- ✅ 응답 시간 < 2초

---

### Task 1.4: HTML 태그 제거 및 날짜 파싱 (10분)

#### 구현 내용

**1. HTML 태그 제거 함수**
```python
import re

def clean_html_tags(text: str) -> str:
    """
    HTML 태그 제거 (<b>, </b> 등)
    
    Args:
        text: HTML 태그가 포함된 문자열
    
    Returns:
        str: 태그가 제거된 순수 텍스트
    """
    # <b>, </b> 등 모든 HTML 태그 제거
    clean_text = re.sub(r'<[^>]+>', '', text)
    return clean_text
```

**2. 날짜 파싱 함수**
```python
from datetime import datetime

def parse_pubdate(pubdate_str: str) -> str:
    """
    pubDate를 YYYY-MM-DD 형식으로 변환
    
    Args:
        pubdate_str: "Mon, 08 Nov 2025 14:50:00 +0900" 형식
    
    Returns:
        str: "2025-11-08" 형식
    """
    # RFC 822 형식 파싱
    dt = datetime.strptime(pubdate_str, "%a, %d %b %Y %H:%M:%S %z")
    return dt.strftime("%Y-%m-%d")
```

**적용:**
```python
# test_basic.py에서 사용
title_clean = clean_html_tags(item['title'])
description_clean = clean_html_tags(item['description'])
date_formatted = parse_pubdate(item['pubDate'])
```

---

### Task 1.5: 결과 검증 및 문서화 (5분)

#### 파일: `STEP1_RESULT.md`

**작성 내용:**
```markdown
# 1단계 결과 보고서

## ✅ 성공 여부
- [x] API 호출 성공
- [x] 10개 뉴스 수집 성공
- [x] 응답 필드 완전성 확인
- [x] HTML 태그 제거 성공
- [x] 날짜 파싱 성공

## 📊 성능 지표
- API 호출 성공률: 100% (10/10)
- 평균 응답 시간: 0.5초
- 수집된 뉴스 개수: 10건
- 데이터 필드 완전성: 100%

## 📝 수집된 데이터 샘플
(실제 수집된 뉴스 3개 정도 붙여넣기)

## 🐛 발견된 이슈
- 없음 (또는 발견된 문제 기록)

## 🎯 다음 단계
2단계: 다중 키워드 및 날짜 필터링
- 6개 종목별 키워드 테스트
- 날짜 범위 필터링
- 관련도 점수 계산
```

---

## 🎯 1단계 완료 기준 (Acceptance Criteria)

### 필수 조건 ✅
- [ ] `.env` 파일 생성 및 API 키 설정
- [ ] `naver_news_api.py` 작성 완료
- [ ] `test_basic.py` 작성 완료
- [ ] "AI" 키워드로 10개 뉴스 수집 성공
- [ ] 응답 필드 완전성 검증 (title, link, pubDate, description)
- [ ] HTML 태그 제거 기능 구현
- [ ] 날짜 파싱 기능 구현
- [ ] `STEP1_RESULT.md` 작성 완료

### 성능 지표 📈
- ✅ API 호출 성공률: 100%
- ✅ 평균 응답 시간: < 2초
- ✅ 데이터 필드 완전성: 100%

---

## 📚 참고 자료

### 필수 문서
1. **`README.md`**: 프로젝트 개요 및 전체 계획
2. **`STEP1_PLAN.md`**: 1단계 세부 작업 계획
3. **네이버 API 문서**: https://developers.naver.com/docs/serviceapi/search/news/news.md

### Python 패키지 문서
- requests: https://requests.readthedocs.io/
- python-dotenv: https://pypi.org/project/python-dotenv/

---

## 🚀 작업 시작 가이드

### 1단계: 파일 확인
```bash
cd /Users/kangsuek/pythonProject/ETFWeeklyReport/backend/prototypes/news_scraper_poc/
ls -la
```

**확인 사항:**
- ✅ `README.md` 존재
- ✅ `STEP1_PLAN.md` 존재
- ✅ `WORK_INSTRUCTION.md` 존재 (현재 파일)

### 2단계: 작업 시작
```bash
# Task 1.1부터 순서대로 진행
1. .env 파일 생성
2. requirements.txt 생성 및 설치
3. naver_news_api.py 작성
4. test_basic.py 작성 및 실행
5. STEP1_RESULT.md 작성
```

### 3단계: 테스트 실행
```bash
python test_basic.py
```

**예상 출력:**
```
========================================
네이버 뉴스 API 테스트
========================================
검색 키워드: AI
검색 결과: 10건 / 전체 1,234,567건
응답 시간: 0.5초
========================================

[1] 제목: ...
    ...
```

### 4단계: 결과 확인
- ✅ 10개 뉴스 수집 성공
- ✅ 모든 필드 존재
- ✅ HTML 태그 제거됨
- ✅ 날짜 파싱 정상

### 5단계: 결과 문서화
- `STEP1_RESULT.md` 작성 완료

---

## ⚠️ 주의사항

### 보안
- ❗ `.env` 파일은 **절대 Git에 커밋하지 않기**
- ❗ `.gitignore`에 `.env` 추가 필수

### API 제한
- 일일 한도: 25,000회
- 현재 테스트는 10~20회 정도 사용 예상
- Rate Limit 초과 시 다음날 재시도

### 에러 대응
- 401/403 에러: Client ID/Secret 재확인
- 429 에러: 일일 한도 초과, 다음날 재시도
- 500 에러: 네이버 서버 문제, 잠시 후 재시도

---

## 📞 문제 발생 시

### 확인 사항
1. Client ID/Secret 정확히 입력했는지
2. `requests` 패키지 설치되었는지
3. 인터넷 연결 정상인지
4. API 엔드포인트 URL 정확한지

### 로그 출력
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## ✅ 완료 후 다음 단계

1단계 완료 후:
- `STEP1_RESULT.md` 내용을 메인 세션에 공유
- 2단계 작업 지시서 받기
- 또는 바로 2단계 진행 (다중 키워드 테스트)

---

**🎉 준비 완료! 지금 바로 Task 1.1부터 시작하세요!**

