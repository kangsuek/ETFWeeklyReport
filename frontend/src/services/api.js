import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const etfApi = {
  getAll: () => api.get('/etfs'),
  getDetail: (ticker) => api.get(`/etfs/${ticker}`),
  getPrices: (ticker, startDate, endDate) => 
    api.get(`/etfs/${ticker}/prices`, { params: { start_date: startDate, end_date: endDate } }),
  getTradingFlow: (ticker, startDate, endDate) => 
    api.get(`/etfs/${ticker}/trading-flow`, { params: { start_date: startDate, end_date: endDate } }),
  getMetrics: (ticker) => api.get(`/etfs/${ticker}/metrics`),
  getNews: (ticker, startDate, endDate) => 
    api.get(`/news/${ticker}`, { params: { start_date: startDate, end_date: endDate } }),
}

export default api
