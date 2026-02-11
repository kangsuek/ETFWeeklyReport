import { Link, useNavigate } from 'react-router-dom'

const COLUMNS = [
  { key: 'name', label: '종목명', sortable: true },
  { key: 'close_price', label: '현재가', sortable: true, align: 'right' },
  { key: 'daily_change_pct', label: '등락률', sortable: true, align: 'right' },
  { key: 'volume', label: '거래량', sortable: true, align: 'right' },
  { key: 'weekly_return', label: '주간수익률', sortable: true, align: 'right' },
  { key: 'foreign_net', label: '외국인', sortable: true, align: 'right' },
  { key: 'institutional_net', label: '기관', sortable: true, align: 'right' },
]

function formatNumber(num) {
  if (num == null) return '-'
  return num.toLocaleString('ko-KR')
}

function formatSignedNumber(num) {
  if (num == null) return '-'
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toLocaleString('ko-KR')}`
}

function formatPercent(val) {
  if (val == null) return '-'
  const arrow = val > 0 ? '▲' : val < 0 ? '▼' : ''
  const sign = val > 0 ? '+' : ''
  return `${arrow} ${sign}${val.toFixed(2)}%`
}

function getChangeColor(val) {
  if (val == null) return 'text-gray-500 dark:text-gray-400'
  if (val > 0) return 'text-red-600 dark:text-red-400'
  if (val < 0) return 'text-blue-600 dark:text-blue-400'
  return 'text-gray-500 dark:text-gray-400'
}

export default function ScreeningTable({ items, total, page, pageSize, sortBy, sortDir, onSort, onPageChange }) {
  const navigate = useNavigate()

  const totalPages = Math.ceil(total / pageSize)

  const SortIcon = ({ column }) => {
    if (sortBy !== column) {
      return <span className="text-gray-300 dark:text-gray-600 ml-0.5">↕</span>
    }
    return <span className="text-primary-500 ml-0.5">{sortDir === 'asc' ? '▲' : '▼'}</span>
  }

  if (!items || items.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-8 text-center transition-colors">
        <p className="text-gray-500 dark:text-gray-400">검색 결과가 없습니다. 필터를 조정해보세요.</p>
      </div>
    )
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden transition-colors">
      {/* 테이블 */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-900">
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className={`px-3 py-2.5 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider ${col.align === 'right' ? 'text-right' : 'text-left'} ${col.sortable ? 'cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 select-none' : ''}`}
                  onClick={() => col.sortable && onSort(col.key)}
                >
                  <span className="inline-flex items-center gap-0.5">
                    {col.label}
                    {col.sortable && <SortIcon column={col.key} />}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {items.map((item) => (
              <tr key={item.ticker} className="transition-colors">
                {/* 종목명 */}
                <td className="px-3 py-2.5">
                  <div>
                    {item.is_registered ? (
                      <Link
                        to={`/etf/${item.ticker}`}
                        className="text-sm font-medium text-primary-600 dark:text-primary-400 hover:underline transition-colors"
                      >
                        {item.name}
                      </Link>
                    ) : (
                      <button
                        onClick={() => navigate('/settings', {
                          state: {
                            addStock: {
                              ticker: item.ticker,
                              name: item.name,
                              type: item.type,
                              theme: item.sector || '',
                            },
                          },
                        })}
                        className="text-sm font-medium text-gray-900 dark:text-gray-100 hover:text-primary-600 dark:hover:text-primary-400 transition-colors text-left"
                      >
                        {item.name}
                      </button>
                    )}
                    <p className="text-xs text-gray-400 dark:text-gray-500">{item.ticker}</p>
                  </div>
                </td>
                {/* 현재가 */}
                <td className="px-3 py-2.5 text-right font-medium text-gray-900 dark:text-gray-100 tabular-nums">
                  {formatNumber(item.close_price)}
                </td>
                {/* 등락률 */}
                <td className={`px-3 py-2.5 text-right font-medium tabular-nums ${getChangeColor(item.daily_change_pct)}`}>
                  {formatPercent(item.daily_change_pct)}
                </td>
                {/* 거래량 */}
                <td className="px-3 py-2.5 text-right text-gray-600 dark:text-gray-400 tabular-nums">
                  {formatNumber(item.volume)}
                </td>
                {/* 주간수익률 */}
                <td className={`px-3 py-2.5 text-right font-medium tabular-nums ${getChangeColor(item.weekly_return)}`}>
                  {formatPercent(item.weekly_return)}
                </td>
                {/* 외국인 */}
                <td className={`px-3 py-2.5 text-right tabular-nums ${getChangeColor(item.foreign_net)}`}>
                  {formatSignedNumber(item.foreign_net)}
                </td>
                {/* 기관 */}
                <td className={`px-3 py-2.5 text-right tabular-nums ${getChangeColor(item.institutional_net)}`}>
                  {formatSignedNumber(item.institutional_net)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            총 {total.toLocaleString()}개 중 {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)}
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="px-2.5 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              이전
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              let pageNum
              if (totalPages <= 5) {
                pageNum = i + 1
              } else if (page <= 3) {
                pageNum = i + 1
              } else if (page >= totalPages - 2) {
                pageNum = totalPages - 4 + i
              } else {
                pageNum = page - 2 + i
              }
              return (
                <button
                  key={pageNum}
                  onClick={() => onPageChange(pageNum)}
                  className={`px-2.5 py-1 text-sm rounded border transition-colors ${
                    page === pageNum
                      ? 'bg-primary-500 text-white border-primary-500'
                      : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  {pageNum}
                </button>
              )
            })}
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="px-2.5 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              다음
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
