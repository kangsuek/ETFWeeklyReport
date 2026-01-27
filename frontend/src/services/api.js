import axios from 'axios'
import {
  DEFAULT_API_TIMEOUT,
  FAST_API_TIMEOUT,
  NORMAL_API_TIMEOUT,
  LONG_API_TIMEOUT,
  ERROR_MESSAGES,
} from '../constants'

// 프록시를 사용하도록 상대 경로로 설정
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

// API Key (환경 변수에서 로드)
const API_KEY = import.meta.env.VITE_API_KEY

// 기본 Axios 인스턴스 생성 (기본 타임아웃 사용)
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: DEFAULT_API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 요청 인터셉터
api.interceptors.request.use(
  (config) => {
    // 디버깅: 종목 목록 수집 요청 로깅
    if (config.url && config.url.includes('ticker-catalog/collect')) {
      console.log('[API] 종목 목록 수집 요청:', {
        method: config.method,
        url: config.url,
        baseURL: config.baseURL,
        fullURL: `${config.baseURL}${config.url}`,
        headers: config.headers
      })
    }
    
    // API Key가 설정된 경우 모든 요청에 추가
    if (API_KEY) {
      config.headers['X-API-Key'] = API_KEY
    }
    return config
  },
  (error) => {
    console.error('[API] 요청 인터셉터 에러:', error)
    return Promise.reject(error)
  }
)

// 응답 인터셉터
api.interceptors.response.use(
  (response) => {
    // 디버깅: 종목 목록 수집 응답 로깅
    if (response.config.url && response.config.url.includes('ticker-catalog/collect')) {
      console.log('[API] 종목 목록 수집 응답 성공:', {
        status: response.status,
        data: response.data
      })
    }
    return response
  },
  (error) => {
    // 디버깅: 종목 목록 수집 에러 로깅
    if (error.config && error.config.url && error.config.url.includes('ticker-catalog/collect')) {
      console.error('[API] 종목 목록 수집 응답 에러:', {
        message: error.message,
        response: error.response,
        request: error.request,
        config: error.config
      })
    }
    
    // 에러 응답 처리
    if (error.response) {
      // 서버 응답이 있는 경우
      const { status, data } = error.response

      switch (status) {
        case 400:
          error.message = data.detail || ERROR_MESSAGES.BAD_REQUEST
          break
        case 401:
          error.message = data.detail || '인증이 필요합니다. API 키를 확인해주세요.'
          break
        case 404:
          error.message = data.detail || ERROR_MESSAGES.NOT_FOUND
          break
        case 500:
          error.message = data.detail || ERROR_MESSAGES.SERVER_ERROR
          break
        default:
          error.message = data.detail || ERROR_MESSAGES.SERVER_ERROR
      }
    } else if (error.request) {
      // 요청은 보냈으나 응답이 없는 경우
      console.error('[API] 서버 응답 없음:', error.request)
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        error.message = ERROR_MESSAGES.TIMEOUT_ERROR
      } else {
        error.message = ERROR_MESSAGES.NETWORK_ERROR
      }
    } else {
      // 요청 설정 중 오류 발생
      console.error('[API] 요청 설정 에러:', error)
      error.message = error.message || ERROR_MESSAGES.SERVER_ERROR
    }

    return Promise.reject(error)
  }
)

// ETF API 서비스
export const etfApi = {
  // 전체 종목 조회 (빠른 조회)
  getAll: () => api.get('/etfs/', { timeout: FAST_API_TIMEOUT }),

  // 개별 종목 정보 (빠른 조회)
  getDetail: (ticker) => api.get(`/etfs/${ticker}`, { timeout: FAST_API_TIMEOUT }),

  // 가격 데이터 조회 (일반 조회)
  getPrices: (ticker, params = {}) => {
    const { startDate, endDate, days } = params
    return api.get(`/etfs/${ticker}/prices`, {
      timeout: NORMAL_API_TIMEOUT,
      params: {
        start_date: startDate,
        end_date: endDate,
        days
      }
    })
  },

  // 매매 동향 조회 (일반 조회)
  getTradingFlow: (ticker, params = {}) => {
    const { startDate, endDate, days } = params
    return api.get(`/etfs/${ticker}/trading-flow`, {
      timeout: NORMAL_API_TIMEOUT,
      params: {
        start_date: startDate,
        end_date: endDate,
        days
      }
    })
  },

  // 종목 지표 조회 (일반 조회)
  getMetrics: (ticker) => api.get(`/etfs/${ticker}/metrics`, { timeout: NORMAL_API_TIMEOUT }),

  // 종목 인사이트 조회 (일반 조회)
  getInsights: (ticker, period = '1m') => 
    api.get(`/etfs/${ticker}/insights`, { 
      timeout: NORMAL_API_TIMEOUT,
      params: { period }
    }),

  // 가격 데이터 수집 트리거 (긴 작업)
  collectPrices: (ticker, days = 10) =>
    api.post(`/etfs/${ticker}/collect`, null, { 
      timeout: LONG_API_TIMEOUT,
      params: { days } 
    }),

  // 매매 동향 수집 트리거 (긴 작업)
  collectTradingFlow: (ticker, days = 10) =>
    api.post(`/etfs/${ticker}/collect-trading-flow`, null, { 
      timeout: LONG_API_TIMEOUT,
      params: { days } 
    }),

  // 종목 비교 (일반 조회)
  compare: (params = {}) => {
    return api.get('/etfs/compare', {
      timeout: NORMAL_API_TIMEOUT,
      params
    })
  },

  // 배치 요약 조회 (일반 조회) - N+1 쿼리 최적화
  getBatchSummary: (tickers, priceDays = 5, newsLimit = 5) => {
    return api.post('/etfs/batch-summary', {
      tickers,
      price_days: priceDays,
      news_limit: newsLimit
    }, {
      timeout: NORMAL_API_TIMEOUT
    })
  },

  // 분봉(시간별 체결) 데이터 조회 (일반 조회)
  getIntraday: (ticker, params = {}) => {
    const { targetDate, autoCollect = true } = params
    return api.get(`/etfs/${ticker}/intraday`, {
      timeout: NORMAL_API_TIMEOUT,
      params: {
        target_date: targetDate,
        auto_collect: autoCollect
      }
    })
  },

  // 분봉 데이터 수집 트리거 (긴 작업)
  collectIntraday: (ticker, pages = 20) =>
    api.post(`/etfs/${ticker}/collect-intraday`, null, {
      timeout: LONG_API_TIMEOUT,
      params: { pages }
    }),
}

// News API 서비스
export const newsApi = {
  // 종목별 뉴스 조회 (일반 조회)
  getByTicker: (ticker, params = {}) => {
    const { startDate, endDate, days, limit } = params
    return api.get(`/news/${ticker}`, {
      timeout: NORMAL_API_TIMEOUT,
      params: {
        start_date: startDate,
        end_date: endDate,
        days,
        limit
      }
    })
  },

  // 전체 뉴스 조회 (추후 구현 시) (일반 조회)
  getAll: (params = {}) => {
    const { startDate, endDate, days, limit } = params
    return api.get('/news', {
      timeout: NORMAL_API_TIMEOUT,
      params: {
        start_date: startDate,
        end_date: endDate,
        days,
        limit
      }
    })
  },

  // 뉴스 수집 트리거 (긴 작업)
  collect: (ticker, days = 7) =>
    api.post(`/news/${ticker}/collect`, null, { 
      timeout: LONG_API_TIMEOUT,
      params: { days } 
    }),
}

// Data Collection API 서비스
export const dataApi = {
  // 전체 종목 데이터 수집 (긴 작업)
  collectAll: (days = 10) =>
    api.post('/data/collect-all', null, { 
      timeout: LONG_API_TIMEOUT,
      params: { days } 
    }),

  // 히스토리 백필 (긴 작업)
  backfill: (days = 90) =>
    api.post('/data/backfill', null, { 
      timeout: LONG_API_TIMEOUT,
      params: { days } 
    }),

  // 수집 상태 조회 (빠른 조회)
  getStatus: () => api.get('/data/status', { timeout: FAST_API_TIMEOUT }),

  // 스케줄러 상태 조회 (빠른 조회)
  getSchedulerStatus: () => api.get('/data/scheduler-status', { timeout: FAST_API_TIMEOUT }),

  // 데이터베이스 통계 조회 (일반 조회)
  getStats: () => api.get('/data/stats', { timeout: NORMAL_API_TIMEOUT }),

  // 캐시 통계 조회 (빠른 조회)
  getCacheStats: () => api.get('/data/cache/stats', { timeout: FAST_API_TIMEOUT }),

  // 데이터베이스 초기화 (위험!) (긴 작업)
  reset: () => api.delete('/data/reset', { timeout: LONG_API_TIMEOUT }),
}

// Health Check API
export const healthApi = {
  check: () => api.get('/health', { timeout: FAST_API_TIMEOUT }),
}

// Settings API 서비스
export const settingsApi = {
  // 종목 목록 조회 (stocks.json 기반) (빠른 조회)
  getStocks: () => api.get('/settings/stocks', { timeout: FAST_API_TIMEOUT }),

  // 종목 추가 (일반 작업)
  createStock: (data) => api.post('/settings/stocks', data, { timeout: NORMAL_API_TIMEOUT }),

  // 종목 수정 (일반 작업)
  updateStock: (ticker, data) => api.put(`/settings/stocks/${ticker}`, data, { timeout: NORMAL_API_TIMEOUT }),

  // 종목 삭제 (일반 작업)
  deleteStock: (ticker) => api.delete(`/settings/stocks/${ticker}`, { timeout: NORMAL_API_TIMEOUT }),

  // 종목 유효성 검증 (네이버 금융 스크래핑) (일반 조회)
  validateTicker: (ticker) => api.get(`/settings/stocks/${ticker}/validate`, { timeout: NORMAL_API_TIMEOUT }),

  // 종목 검색 (자동완성용) (빠른 조회)
  searchStocks: (query, type = null) => {
    const params = { q: query }
    if (type) params.type = type
    return api.get('/settings/stocks/search', { params, timeout: FAST_API_TIMEOUT })
  },

  // 종목 목록 수집 트리거 (긴 작업)
  collectTickerCatalog: () => api.post('/settings/ticker-catalog/collect', null, { timeout: LONG_API_TIMEOUT }),

  // 종목 순서 변경 (일반 작업)
  reorderStocks: (tickers) => api.post('/settings/stocks/reorder', tickers, { timeout: NORMAL_API_TIMEOUT }),
}

// 단순화된 API 인터페이스
export const apiService = {
  getETFs: async () => {
    const response = await etfApi.getAll()
    return response.data
  },
  compareETFs: async (params) => {
    const response = await etfApi.compare(params)
    return response.data
  },
}

// 통합 API 객체 (편의를 위해 export)
export { api }

export default apiService
