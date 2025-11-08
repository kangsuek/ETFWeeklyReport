# 1단계 세부 작업 계획: 네이버 뉴스 API 기본 구현

## 📋 목표
네이버 검색 API를 사용한 기본 뉴스 수집 기능 구현 및 검증

## ⏱️ 예상 소요 시간: 1시간

---

## 📝 세부 작업 항목

### Task 1.1: 프로토타입 환경 설정 (10분)

#### 작업 내용
1. **디렉토리 구조 생성**
   ```
   backend/prototypes/news_scraper_poc/
   ├── README.md (완료)
   ├── STEP1_PLAN.md (현재 파일)
   ├── .env (생성 예정)
   ├── requirements.txt (생성 예정)
   ├── naver_news_api.py (생성 예정)
   └── test_basic.py (생성 예정)
   ```

2. **`.env` 파일 생성**
   ```env
   NAVER_CLIENT_ID=pQbDBJ1we0Cpv5l54xne
   NAVER_CLIENT_SECRET=GcptomaJI1
   ```

3. **`requirements.txt` 생성**
   ```txt
   requests==2.31.0
   python-dotenv==1.0.0
   ```

#### 완료 조건
- [ ] 디렉토리 구조 생성 완료
- [ ] `.env` 파일 생성 및 API 키 저장
- [ ] `requirements.txt` 생성
- [ ] 패키지 설치 확인 (`pip install -r requirements.txt`)

---

### Task 1.2: 기본 API 호출 스크립트 작성 (20분)

#### 작업 내용
1. **`naver_news_api.py` 생성**
   - 환경 변수 로드 (`python-dotenv`)
   - API 호출 함수 구현
   - 응답 데이터 파싱
   - 에러 핸들링

2. **구현할 함수**
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
           query: 검색 키워드
           display: 검색 결과 개수 (1-100)
           start: 검색 시작 위치 (1-1000)
           sort: 정렬 방식 (sim: 정확도, date: 날짜)
       
       Returns:
           dict: API 응답 JSON
       """
   ```

3. **에러 코드 처리**
   - 401: 인증 실패 (Client ID/Secret 오류)
   - 403: API 권한 없음
   - 429: Rate Limit 초과
   - 500: 서버 오류

#### 완료 조건
- [ ] `naver_news_api.py` 스크립트 작성 완료
- [ ] `search_news()` 함수 구현
- [ ] HTTP 요청 헤더 설정 (Client ID/Secret)
- [ ] JSON 응답 파싱 구현
- [ ] 에러 핸들링 구현 (try-except)

---

### Task 1.3: 단일 키워드 테스트 (15분)

#### 작업 내용
1. **테스트 스크립트 작성** (`test_basic.py`)
   - 단일 키워드 테스트: "AI"
   - 응답 필드 검증
   - 데이터 출력 (표 형식)

2. **검증 항목**
   - ✅ API 호출 성공 (HTTP 200)
   - ✅ 응답 필드 존재 (title, link, pubDate, description)
   - ✅ 검색 결과 개수 (display 값과 일치)
   - ✅ 응답 시간 < 2초

3. **출력 형식**
   ```
   ========================================
   검색 키워드: AI
   검색 결과: 10건 / 전체 1,234,567건
   응답 시간: 0.5초
   ========================================
   
   [1] 제목: AI 기술 발전...
       URL: https://...
       날짜: 2025-11-08
       출처: 연합뉴스
       요약: AI 기술이 급속도로...
   
   [2] ...
   ```

#### 완료 조건
- [ ] `test_basic.py` 작성 완료
- [ ] "AI" 키워드로 10개 뉴스 수집 성공
- [ ] 응답 필드 완전성 검증 (title, link, pubDate)
- [ ] 결과 출력 확인

---

### Task 1.4: HTML 태그 제거 및 날짜 파싱 (10분)

#### 작업 내용
1. **HTML 태그 제거**
   - 제목/요약에서 `<b>`, `</b>` 제거
   - 정규식 또는 `html.unescape()` 사용

2. **날짜 파싱**
   - 입력: `"Mon, 26 Sep 2016 07:50:00 +0900"`
   - 출력: `datetime` 객체 또는 `"2016-09-26"`

3. **유틸리티 함수 추가**
   ```python
   def clean_html_tags(text: str) -> str:
       """HTML 태그 제거"""
   
   def parse_pubdate(pubdate_str: str) -> str:
       """pubDate를 YYYY-MM-DD 형식으로 변환"""
   ```

#### 완료 조건
- [ ] `clean_html_tags()` 함수 구현
- [ ] `parse_pubdate()` 함수 구현
- [ ] 테스트에 적용 및 출력 확인

---

### Task 1.5: 결과 검증 및 문서화 (5분)

#### 작업 내용
1. **성공 지표 확인**
   - ✅ 10개 이상 뉴스 수집 성공
   - ✅ 필드 완전성: title, link, pubDate, description
   - ✅ 응답 시간 < 2초
   - ✅ 에러 핸들링 동작 확인

2. **결과 문서 작성** (`STEP1_RESULT.md`)
   - 성공/실패 여부
   - 수집된 데이터 샘플
   - 발견된 이슈
   - 다음 단계 계획

#### 완료 조건
- [ ] 모든 성공 지표 달성
- [ ] `STEP1_RESULT.md` 작성 완료
- [ ] 다음 단계(Task 2) 준비 완료

---

## 🎯 1단계 완료 기준 (Acceptance Criteria)

### 필수 조건
- [x] 프로토타입 디렉토리 구조 생성
- [ ] `.env` 파일 생성 및 API 키 설정
- [ ] `naver_news_api.py` 스크립트 작성
- [ ] 단일 키워드 ("AI")로 10개 뉴스 수집 성공
- [ ] 응답 필드 완전성 검증 (title, link, pubDate, description)
- [ ] HTML 태그 제거 및 날짜 파싱 구현
- [ ] 에러 핸들링 동작 확인
- [ ] 결과 문서 작성 (`STEP1_RESULT.md`)

### 성능 지표
- ✅ API 호출 성공률: 100%
- ✅ 평균 응답 시간: < 2초
- ✅ 데이터 필드 완전성: 100%

---

## 📚 참고 자료

- [네이버 검색 API - 뉴스](https://developers.naver.com/docs/serviceapi/search/news/news.md)
- [Python requests 문서](https://requests.readthedocs.io/)
- [Python-dotenv 문서](https://pypi.org/project/python-dotenv/)

---

## 🚀 시작!

이제 Task 1.1부터 시작합니다!

