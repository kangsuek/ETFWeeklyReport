import { useQuery } from '@tanstack/react-query'
import { etfApi } from '../services/api'
import ETFCard from '../components/etf/ETFCard'

export default function Dashboard() {
  const { data: etfs, isLoading, error } = useQuery({
    queryKey: ['etfs'],
    queryFn: async () => {
      const response = await etfApi.getAll()
      return response.data
    },
  })

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-red-600 text-center">
        Error loading ETFs: {error.message}
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">ETF Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {etfs?.map((etf) => (
          <ETFCard key={etf.ticker} etf={etf} />
        ))}
      </div>
    </div>
  )
}
