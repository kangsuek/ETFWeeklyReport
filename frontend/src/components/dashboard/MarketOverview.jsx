import { useQuery } from '@tanstack/react-query'
import { marketApi } from '../../services/api'

/**
 * 개별 지수 카드 컴포넌트
 */
const IndexCard = ({ index }) => {
  const isPositive = index.change > 0
  const isNegative = index.change < 0

  const changeColor = isPositive
    ? 'text-red-600 dark:text-red-400'
    : isNegative
    ? 'text-blue-600 dark:text-blue-400'
    : 'text-gray-500 dark:text-gray-400'

  const bgColor = isPositive
    ? 'bg-red-50 dark:bg-red-900/10 border-red-100 dark:border-red-800/30'
    : isNegative
    ? 'bg-blue-50 dark:bg-blue-900/10 border-blue-100 dark:border-blue-800/30'
    : 'bg-gray-50 dark:bg-gray-700 border-gray-100 dark:border-gray-600'

  const changeSign = isPositive ? '+' : ''

  return (
    <div className={`flex items-center justify-between px-4 py-2.5 rounded-lg border ${bgColor}`}>
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">{index.name}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm font-bold text-gray-900 dark:text-gray-100">
          {index.close_price.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
        <span className={`text-xs font-semibold ${changeColor}`}>
          {changeSign}{index.change.toLocaleString('ko-KR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          {' '}
          ({changeSign}{index.change_ratio.toFixed(2)}%)
        </span>
      </div>
    </div>
  )
}

/**
 * MarketOverview 컴포넌트
 * KOSPI / KOSDAQ 지수 현황을 대시보드 상단에 표시합니다.
 */
export default function MarketOverview() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['market-overview'],
    queryFn: async () => {
      const response = await marketApi.getOverview()
      return response.data
    },
    staleTime: 30 * 1000, // 30초
    refetchInterval: 60 * 1000, // 1분마다 자동 갱신
    retry: 1,
  })

  if (isLoading) {
    return (
      <div className="mb-4 flex gap-3">
        {[1, 2].map((i) => (
          <div key={i} className="flex-1 h-10 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError || !data?.indices || data.indices.length === 0) {
    return null // 실패 시 조용히 숨김 (UI 방해 금지)
  }

  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">시장 현황</span>
        <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        {data.indices.map((index) => (
          <IndexCard key={index.code} index={index} />
        ))}
      </div>
    </div>
  )
}
