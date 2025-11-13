import { useState, useMemo } from 'react'
import PropTypes from 'prop-types'

/**
 * ComparisonTable Component
 *
 * 종목별 성과 비교 테이블
 *
 * @param {Object} statistics - { ticker: { period_return, annualized_return, volatility, ... } }
 * @param {Object} tickerInfo - { ticker: { name, ... } }
 */
export default function ComparisonTable({ statistics, tickerInfo }) {
  const [sortBy, setSortBy] = useState('period_return')
  const [sortDirection, setSortDirection] = useState('desc')

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortDirection('desc')
    }
  }

  // 정렬된 데이터
  const sortedData = useMemo(() => {
    if (!statistics) return []

    const dataArray = Object.entries(statistics).map(([ticker, stats]) => ({
      ticker,
      ...stats,
      name: tickerInfo[ticker]?.name || ticker,
    }))

    return dataArray.sort((a, b) => {
      const aValue = a[sortBy] || 0
      const bValue = b[sortBy] || 0

      if (sortDirection === 'asc') {
        return aValue - bValue
      }
      return bValue - aValue
    })
  }, [statistics, tickerInfo, sortBy, sortDirection])

  // 최고 성과 강조
  const getBestValue = (column) => {
    if (sortedData.length === 0) return null

    // max_drawdown은 작을수록 좋음 (음수이므로 큰 값이 좋음)
    if (column === 'max_drawdown') {
      return Math.max(...sortedData.map(d => d[column] || -Infinity))
    }

    // 나머지는 클수록 좋음
    return Math.max(...sortedData.map(d => d[column] || -Infinity))
  }

  const formatNumber = (value, decimals = 2) => {
    if (value === null || value === undefined) return 'N/A'
    return value.toFixed(decimals)
  }

  const formatPercent = (value, decimals = 2) => {
    if (value === null || value === undefined) return 'N/A'
    const formatted = value.toFixed(decimals)
    return value >= 0 ? `+${formatted}%` : `${formatted}%`
  }

  const SortIcon = ({ column }) => {
    if (sortBy !== column) return <span className="text-gray-400">↕</span>
    return sortDirection === 'asc' ? <span>↑</span> : <span>↓</span>
  }

  if (!statistics || Object.keys(statistics).length === 0) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          성과 비교
        </h3>
        <div className="flex items-center justify-center py-16 text-gray-500 dark:text-gray-400">
          데이터가 없습니다
        </div>
      </div>
    )
  }

  const columns = [
    { key: 'period_return', label: '기간 수익률', format: formatPercent },
    { key: 'annualized_return', label: '연환산 수익률', format: formatPercent },
    { key: 'volatility', label: '변동성', format: formatPercent },
    { key: 'max_drawdown', label: '최대 낙폭', format: formatPercent },
    { key: 'sharpe_ratio', label: '샤프 비율', format: formatNumber },
  ]

  return (
    <div className="card">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          성과 비교
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          종목별 수익률, 변동성, 샤프비율 등 주요 지표 비교
        </p>
      </div>

      {/* Desktop Table */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="py-3 px-4 text-left text-sm font-semibold text-gray-900 dark:text-white">
                종목명
              </th>
              {columns.map(col => (
                <th
                  key={col.key}
                  onClick={() => handleSort(col.key)}
                  className="py-3 px-4 text-right text-sm font-semibold text-gray-900 dark:text-white cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <div className="flex items-center justify-end gap-1">
                    {col.label}
                    <SortIcon column={col.key} />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedData.map((row, idx) => {
              return (
                <tr
                  key={row.ticker}
                  className={`border-b border-gray-100 dark:border-gray-800 ${
                    idx % 2 === 0 ? 'bg-white dark:bg-gray-900' : 'bg-gray-50 dark:bg-gray-800/50'
                  }`}
                >
                  <td className="py-3 px-4">
                    <div className="font-medium text-gray-900 dark:text-white">
                      {row.name}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {row.ticker}
                    </div>
                  </td>
                  {columns.map(col => {
                    const value = row[col.key]
                    const isBest = value === getBestValue(col.key)
                    const isReturn = col.key.includes('return')
                    const isDrawdown = col.key === 'max_drawdown'

                    return (
                      <td
                        key={col.key}
                        className={`py-3 px-4 text-right ${
                          isBest ? 'bg-blue-50 dark:bg-blue-900/20 font-semibold' : ''
                        }`}
                      >
                        <span className={`${
                          isReturn
                            ? value >= 0
                              ? 'text-red-600 dark:text-red-400'
                              : 'text-blue-600 dark:text-blue-400'
                            : isDrawdown
                            ? 'text-orange-600 dark:text-orange-400'
                            : 'text-gray-900 dark:text-white'
                        }`}>
                          {col.format(value)}
                        </span>
                        {isBest && (
                          <span className="ml-2 text-xs text-blue-600 dark:text-blue-400">
                            ⭐
                          </span>
                        )}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Cards */}
      <div className="md:hidden space-y-4">
        {sortedData.map((row) => (
          <div
            key={row.ticker}
            className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
          >
            <div className="font-medium text-gray-900 dark:text-white mb-2">
              {row.name}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mb-3">
              {row.ticker}
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {columns.map(col => {
                const value = row[col.key]
                const isBest = value === getBestValue(col.key)
                const isReturn = col.key.includes('return')
                const isDrawdown = col.key === 'max_drawdown'

                return (
                  <div key={col.key}>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {col.label}
                    </div>
                    <div className={`font-medium ${
                      isReturn
                        ? value >= 0
                          ? 'text-red-600 dark:text-red-400'
                          : 'text-blue-600 dark:text-blue-400'
                        : isDrawdown
                        ? 'text-orange-600 dark:text-orange-400'
                        : 'text-gray-900 dark:text-white'
                    }`}>
                      {col.format(value)}
                      {isBest && <span className="ml-1 text-xs">⭐</span>}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-600 dark:text-gray-400">
        <p>
          ⭐ = 최고 성과 지표 |
          <span className="text-red-600 dark:text-red-400"> 빨강</span> = 상승 |
          <span className="text-blue-600 dark:text-blue-400"> 파랑</span> = 하락
        </p>
        <p className="mt-1">
          샤프 비율: 무위험 수익률 3% 가정
        </p>
      </div>
    </div>
  )
}

ComparisonTable.propTypes = {
  statistics: PropTypes.object,
  tickerInfo: PropTypes.object.isRequired,
}

ComparisonTable.defaultProps = {
  statistics: null,
  tickerInfo: {},
}
