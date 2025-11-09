import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { etfApi } from '../../services/api'

export default function ETFCard({ etf }) {
  // 최신 가격 데이터 조회 (5일치 - 주간 수익률 계산용)
  const { data: prices, isLoading } = useQuery({
    queryKey: ['prices', etf.ticker],
    queryFn: async () => {
      const response = await etfApi.getPrices(etf.ticker, { days: 5 })
      return response.data
    },
    retry: 1,
    staleTime: 60000, // 1분간 캐시
  })

  // 최신 가격 데이터 (첫 번째 항목)
  const latestPrice = prices?.[0]

  // 주간 수익률 계산 (5일 전과 비교)
  const weeklyReturn = prices && prices.length >= 2
    ? ((prices[0].close_price - prices[prices.length - 1].close_price) / prices[prices.length - 1].close_price) * 100
    : null

  // 등락률에 따른 색상 결정
  const getChangeColor = (changePct) => {
    if (!changePct) return 'text-gray-600'
    return changePct > 0 ? 'text-red-600' : changePct < 0 ? 'text-blue-600' : 'text-gray-600'
  }

  // 등락률 포맷팅
  const formatChange = (changePct) => {
    if (!changePct) return '0.00%'
    const sign = changePct > 0 ? '+' : ''
    return `${sign}${changePct.toFixed(2)}%`
  }

  // 가격 포맷팅 (천 단위 콤마)
  const formatPrice = (price) => {
    if (!price) return '-'
    return new Intl.NumberFormat('ko-KR').format(price)
  }

  // 거래량 포맷팅 (천 단위)
  const formatVolume = (volume) => {
    if (!volume) return '-'
    if (volume >= 1000000) {
      return `${(volume / 1000000).toFixed(1)}M`
    } else if (volume >= 1000) {
      return `${(volume / 1000).toFixed(0)}K`
    }
    return volume.toString()
  }

  return (
    <Link to={`/etf/${etf.ticker}`}>
      <div className="card hover:shadow-xl hover:scale-105 transition-all duration-200 cursor-pointer">
        {/* 헤더: 종목명 + 타입 뱃지 */}
        <div className="mb-3">
          <div className="flex items-start justify-between mb-2">
            <h3 className="text-lg font-bold flex-1 leading-tight">{etf.name}</h3>
            <span className={`text-xs px-2 py-1 rounded-full ml-2 flex-shrink-0 ${
              etf.type === 'ETF'
                ? 'bg-blue-100 text-blue-800'
                : 'bg-purple-100 text-purple-800'
            }`}>
              {etf.type}
            </span>
          </div>
          <p className="text-sm text-gray-600">{etf.theme}</p>
        </div>

        {/* 가격 정보 */}
        {isLoading ? (
          <div className="py-4">
            <div className="h-4 bg-gray-200 rounded animate-pulse mb-2"></div>
            <div className="h-3 bg-gray-200 rounded animate-pulse w-3/4 mb-2"></div>
            <div className="h-3 bg-gray-200 rounded animate-pulse w-1/2"></div>
          </div>
        ) : latestPrice ? (
          <div className="mb-4 py-3 border-t border-b border-gray-100">
            {/* 종가 & 등락률 */}
            <div className="flex items-baseline justify-between mb-2">
              <span className="text-2xl font-bold">{formatPrice(latestPrice.close_price)}</span>
              <span className={`text-sm font-semibold ${getChangeColor(latestPrice.daily_change_pct)}`}>
                {formatChange(latestPrice.daily_change_pct)}
              </span>
            </div>

            {/* 시가/고가/저가 */}
            <div className="grid grid-cols-3 gap-2 mb-2 text-xs">
              <div>
                <span className="text-gray-500">시가</span>
                <div className="font-medium">{formatPrice(latestPrice.open_price)}</div>
              </div>
              <div>
                <span className="text-gray-500">고가</span>
                <div className="font-medium text-red-600">{formatPrice(latestPrice.high_price)}</div>
              </div>
              <div>
                <span className="text-gray-500">저가</span>
                <div className="font-medium text-blue-600">{formatPrice(latestPrice.low_price)}</div>
              </div>
            </div>

            {/* 거래량 & 주간수익률 */}
            <div className="flex justify-between text-xs text-gray-500 border-t border-gray-100 pt-2">
              <span>거래량: {formatVolume(latestPrice.volume)}</span>
              {weeklyReturn !== null && (
                <span className={`font-semibold ${getChangeColor(weeklyReturn)}`}>
                  주간: {formatChange(weeklyReturn)}
                </span>
              )}
            </div>

            {/* 날짜 */}
            <div className="text-xs text-gray-400 mt-1">{latestPrice.date}</div>
          </div>
        ) : (
          <div className="py-4 text-center text-sm text-gray-400">
            가격 정보 없음
          </div>
        )}

        {/* 하단 정보 */}
        <div className="flex justify-between items-center text-xs text-gray-500">
          <span>{etf.ticker}</span>
          {etf.expense_ratio && <span>수수료: {etf.expense_ratio}%</span>}
        </div>
      </div>
    </Link>
  )
}
