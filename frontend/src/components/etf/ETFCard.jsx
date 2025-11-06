import { Link } from 'react-router-dom'

export default function ETFCard({ etf }) {
  return (
    <Link to={`/etf/${etf.ticker}`}>
      <div className="card hover:shadow-lg transition-shadow cursor-pointer">
        <h3 className="text-lg font-bold mb-2">{etf.name}</h3>
        <p className="text-sm text-gray-600 mb-4">{etf.theme}</p>
        <div className="flex justify-between items-center">
          <span className="text-xs text-gray-500">Ticker: {etf.ticker}</span>
          <span className="text-xs text-gray-500">Fee: {etf.expense_ratio}%</span>
        </div>
      </div>
    </Link>
  )
}
