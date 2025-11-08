# 뉴스 스크래핑 POC (Proof of Concept)

## 목표
네이버 검색 API를 사용한 실시간 뉴스 수집 가능성 검증

## 개발 전략
1. **프로토타입 우선 개발** - 메인 코드와 분리
2. **네이버 공식 API 사용** - Selenium/Playwright 불필요
3. **성공 시 메인 코드 통합**
4. **실패 시 대안 검토**

## 네이버 검색 API 스펙

### API 정보
- **문서**: https://developers.naver.com/docs/serviceapi/search/news/news.md
- **Endpoint**: `https://openapi.naver.com/v1/search/news.json`
- **Method**: GET
- **일일 한도**: 25,000회 (무료)

### 요청 헤더
```
X-Naver-Client-Id: {CLIENT_ID}
X-Naver-Client-Secret: {CLIENT_SECRET}
```

### 쿼리 파라미터
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| query | String | Y | 검색어 (UTF-8 인코딩) |
| display | Integer | N | 검색 결과 개수 (기본: 10, 최대: 100) |
| start | Integer | N | 검색 시작 위치 (기본: 1, 최대: 1000) |
| sort | String | N | 정렬 (sim: 정확도, date: 날짜) |

### 응답 필드 (JSON)
```json
{
  "lastBuildDate": "Mon, 26 Sep 2016 11:01:35 +0900",
  "total": 2566589,
  "start": 1,
  "display": 10,
  "items": [
    {
      "title": "국내 <b>주식</b>형펀드서 사흘째 자금 순유출",
      "originallink": "http://...",
      "link": "http://...",
      "description": "...",
      "pubDate": "Mon, 26 Sep 2016 07:50:00 +0900"
    }
  ]
}
```

## 1단계: 기본 API 호출 구현

### 체크리스트
- [ ] 프로토타입 디렉토리 구조 생성
- [ ] `.env` 파일 설정 (Client ID/Secret)
- [ ] 의존성 패키지 확인 (`requests`, `python-dotenv`)
- [ ] 기본 API 호출 스크립트 작성
- [ ] 단일 키워드 테스트 ("AI")
- [ ] 응답 데이터 파싱 및 출력
- [ ] 에러 핸들링 (401, 403, 429, 500)
- [ ] 결과 검증 및 문서화

### 예상 결과
- 10~20개 뉴스 수집 성공
- 응답 시간 < 1초
- 필드 완전성: 제목, URL, 날짜, 출처, 요약

## 2단계: 다중 키워드 및 날짜 필터링

### 체크리스트
- [ ] 6개 종목별 키워드 테스트
- [ ] 날짜 범위 필터링 (최근 N일)
- [ ] 페이지네이션 처리 (start 파라미터)
- [ ] 관련도 점수 계산
- [ ] Rate Limiting 구현

## 3단계: 메인 코드 통합

### 체크리스트
- [ ] `app/services/news_scraper.py` 수정
- [ ] Mock 코드 제거 및 API 코드 통합
- [ ] 기존 테스트 수정
- [ ] 통합 테스트 실행
- [ ] 문서 업데이트

## 참고 자료
- [네이버 검색 API 뉴스](https://developers.naver.com/docs/serviceapi/search/news/news.md)
- [네이버 개발자 센터](https://developers.naver.com/)

