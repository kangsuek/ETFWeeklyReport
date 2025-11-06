import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { etfApi } from '../services/api'

export default function ETFDetail() {
  const { ticker } = useParams()
  
  const { data: etf, isLoading } = useQuery({
    queryKey: ['etf', ticker],
    queryFn: async () => {
      const response = await etfApi.getDetail(ticker)
      return response.data
    },
  })

  if (isLoading) return <div>Loading...</div>

  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">{etf?.name}</h1>
      <div className="card">
        <p>Ticker: {etf?.ticker}</p>
        <p>Theme: {etf?.theme}</p>
        <p>Expense Ratio: {etf?.expense_ratio}%</p>
      </div>
    </div>
  )
}
