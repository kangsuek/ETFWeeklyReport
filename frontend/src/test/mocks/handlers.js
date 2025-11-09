import { http, HttpResponse } from 'msw'

const BASE_URL = 'http://localhost:8000/api'

// Mock data
const mockETFData = [
  {
    code: '487240',
    name: '삼성 KODEX AI전력핵심설비 ETF',
    current_price: 15250,
    change_rate: 2.34,
    volume: 1250000,
    market_cap: '5조 3000억',
    last_updated: '2025-11-10T09:00:00',
  },
  {
    code: '466920',
    name: '신한 SOL 조선TOP3플러스 ETF',
    current_price: 12800,
    change_rate: -1.15,
    volume: 980000,
    market_cap: '2조 8000억',
    last_updated: '2025-11-10T09:00:00',
  },
]

const mockStockData = [
  {
    code: '042660',
    name: '한화오션',
    current_price: 45300,
    change_rate: 3.21,
    volume: 2340000,
    market_cap: '12조 5000억',
    last_updated: '2025-11-10T09:00:00',
  },
  {
    code: '034020',
    name: '두산에너빌리티',
    current_price: 28900,
    change_rate: 1.89,
    volume: 1890000,
    market_cap: '8조 2000억',
    last_updated: '2025-11-10T09:00:00',
  },
]

const mockHistoricalData = [
  {
    date: '2025-11-04',
    close_price: 14950,
    volume: 1100000,
  },
  {
    date: '2025-11-05',
    close_price: 15100,
    volume: 1200000,
  },
  {
    date: '2025-11-06',
    close_price: 15050,
    volume: 1150000,
  },
  {
    date: '2025-11-07',
    close_price: 15200,
    volume: 1300000,
  },
  {
    date: '2025-11-10',
    close_price: 15250,
    volume: 1250000,
  },
]

export const handlers = [
  // GET /api/etfs/ - 모든 ETF 목록 (슬래시 포함)
  http.get(`${BASE_URL}/etfs/`, () => {
    return HttpResponse.json(mockETFData)
  }),

  // GET /api/etfs - 모든 ETF 목록 (슬래시 없음)
  http.get(`${BASE_URL}/etfs`, () => {
    return HttpResponse.json(mockETFData)
  }),

  // GET /api/data/scheduler-status - 스케줄러 상태
  http.get(`${BASE_URL}/data/scheduler-status`, () => {
    return HttpResponse.json({
      scheduler: {
        last_collection_time: '2025-11-10T09:00:00',
        next_collection_time: '2025-11-10T15:00:00',
      },
    })
  }),

  // GET /api/etfs/:code/prices - 가격 데이터
  http.get(`${BASE_URL}/etfs/:code/prices`, () => {
    return HttpResponse.json(mockHistoricalData)
  }),

  // GET /api/etfs/:code/trading-flow - 매매 동향
  http.get(`${BASE_URL}/etfs/:code/trading-flow`, () => {
    return HttpResponse.json([
      {
        date: '2025-11-10',
        individual_net: 15000000,
        institutional_net: -8000000,
        foreign_net: -7000000,
      },
    ])
  }),

  // GET /api/news/:code - 뉴스 (ticker 포함)
  http.get(`${BASE_URL}/news/:code`, () => {
    return HttpResponse.json([
      {
        id: 1,
        title: 'AI 전력 수요 급증, ETF 상승세',
        published_at: '2025-11-10T09:00:00',
      },
      {
        id: 2,
        title: '데이터센터 전력 인프라 투자 확대',
        published_at: '2025-11-09T14:30:00',
      },
    ])
  }),

  // GET /api/etfs/:code - 특정 ETF 상세
  http.get(`${BASE_URL}/etfs/:code`, ({ params }) => {
    const { code } = params
    const etf = mockETFData.find(e => e.code === code)
    if (etf) {
      return HttpResponse.json(etf)
    }
    return new HttpResponse(null, { status: 404 })
  }),
]
