import axios from 'axios'

// 프록시를 사용하도록 상대 경로로 설정
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

// Axios 인스턴스 생성
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60초 타임아웃 (자동 수집 지원)
  headers: {
    'Content-Type': 'application/json',
  },
})

// 요청 인터셉터
api.interceptors.request.use(
  (config) => {
    // 요청 전 처리 (예: 인증 토큰 추가)
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 응답 인터셉터
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // 에러 응답 처리
    if (error.response) {
      // 서버 응답이 있는 경우
      const { status, data } = error.response

      switch (status) {
        case 400:
          error.message = data.detail || '잘못된 요청입니다.'
          break
        case 404:
          error.message = data.detail || '요청한 리소스를 찾을 수 없습니다.'
          break
        case 500:
          error.message = '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
          break
        default:
          error.message = data.detail || '알 수 없는 오류가 발생했습니다.'
      }
    } else if (error.request) {
      // 요청은 보냈으나 응답이 없는 경우
      error.message = '서버와 연결할 수 없습니다. 네트워크 연결을 확인해주세요.'
    } else {
      // 요청 설정 중 오류 발생
      error.message = error.message || '요청 중 오류가 발생했습니다.'
    }

    return Promise.reject(error)
  }
)

// ETF API 서비스
export const etfApi = {
  // 전체 종목 조회
  getAll: () => api.get('/etfs/'),

  // 개별 종목 정보
  getDetail: (ticker) => api.get(`/etfs/${ticker}`),

  // 가격 데이터 조회
  getPrices: (ticker, params = {}) => {
    const { startDate, endDate, days } = params
    return api.get(`/etfs/${ticker}/prices`, {
      params: {
        start_date: startDate,
        end_date: endDate,
        days
      }
    })
  },

  // 매매 동향 조회
  getTradingFlow: (ticker, params = {}) => {
    const { startDate, endDate, days } = params
    return api.get(`/etfs/${ticker}/trading-flow`, {
      params: {
        start_date: startDate,
        end_date: endDate,
        days
      }
    })
  },

  // 종목 지표 조회
  getMetrics: (ticker) => api.get(`/etfs/${ticker}/metrics`),

  // 가격 데이터 수집 트리거
  collectPrices: (ticker, days = 10) =>
    api.post(`/etfs/${ticker}/collect`, null, { params: { days } }),

  // 매매 동향 수집 트리거
  collectTradingFlow: (ticker, days = 10) =>
    api.post(`/etfs/${ticker}/collect-trading-flow`, null, { params: { days } }),
}

// News API 서비스
export const newsApi = {
  // 종목별 뉴스 조회
  getByTicker: (ticker, params = {}) => {
    const { startDate, endDate, days, limit } = params
    return api.get(`/news/${ticker}`, {
      params: {
        start_date: startDate,
        end_date: endDate,
        days,
        limit
      }
    })
  },

  // 전체 뉴스 조회 (추후 구현 시)
  getAll: (params = {}) => {
    const { startDate, endDate, days, limit } = params
    return api.get('/news', {
      params: {
        start_date: startDate,
        end_date: endDate,
        days,
        limit
      }
    })
  },

  // 뉴스 수집 트리거
  collect: (ticker, days = 7) =>
    api.post(`/news/${ticker}/collect`, null, { params: { days } }),
}

// Data Collection API 서비스
export const dataApi = {
  // 전체 종목 데이터 수집
  collectAll: (days = 10) =>
    api.post('/data/collect-all', null, { params: { days } }),

  // 히스토리 백필
  backfill: (days = 90) =>
    api.post('/data/backfill', null, { params: { days } }),

  // 수집 상태 조회
  getStatus: () => api.get('/data/status'),

  // 스케줄러 상태 조회 (마지막 수집 시간 포함)
  getSchedulerStatus: () => api.get('/data/scheduler-status'),

  // 데이터베이스 통계 조회
  getStats: () => api.get('/data/stats'),

  // 데이터베이스 초기화 (위험!)
  reset: () => api.delete('/data/reset'),
}

// Health Check API
export const healthApi = {
  check: () => api.get('/health'),
}

// Settings API 서비스
export const settingsApi = {
  // 종목 추가
  createStock: (data) => api.post('/settings/stocks', data),

  // 종목 수정
  updateStock: (ticker, data) => api.put(`/settings/stocks/${ticker}`, data),

  // 종목 삭제
  deleteStock: (ticker) => api.delete(`/settings/stocks/${ticker}`),

  // 종목 유효성 검증 (네이버 금융 스크래핑)
  validateTicker: (ticker) => api.get(`/settings/stocks/${ticker}/validate`),
}

export default api
