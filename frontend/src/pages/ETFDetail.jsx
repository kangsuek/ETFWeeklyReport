import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { etfApi } from '../services/api'
import PageHeader from '../components/common/PageHeader'
import Spinner from '../components/common/Spinner'

export default function ETFDetail() {
  const { ticker } = useParams()

  const { data: etf, isLoading } = useQuery({
    queryKey: ['etf', ticker],
    queryFn: async () => {
      const response = await etfApi.getDetail(ticker)
      return response.data
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="animate-fadeIn">
      <PageHeader
        title={etf?.name || 'ETF 상세'}
        subtitle={`${etf?.ticker} · ${etf?.theme}`}
      />
      <div className="card">
        <div className="space-y-4">
          <div>
            <span className="text-sm text-gray-500">티커</span>
            <p className="text-lg font-semibold">{etf?.ticker}</p>
          </div>
          <div>
            <span className="text-sm text-gray-500">테마</span>
            <p className="text-lg font-semibold">{etf?.theme}</p>
          </div>
          <div>
            <span className="text-sm text-gray-500">운용보수</span>
            <p className="text-lg font-semibold">{etf?.expense_ratio}%</p>
          </div>
        </div>
      </div>
    </div>
  )
}
