import { useState, useEffect } from 'react'

const MARKET_TABS = [
  { value: 'ETF', label: 'ETF' },
  { value: 'KOSPI', label: 'KOSPI' },
  { value: 'KOSDAQ', label: 'KOSDAQ' },
  { value: 'ALL', label: '전체' },
]

export default function ScreeningFilters({ filters, onFilterChange, onReset, lastUpdated }) {
  const [localQ, setLocalQ] = useState(filters.q || '')
  const [localMinWR, setLocalMinWR] = useState(filters.min_weekly_return ?? '')
  const [localMaxWR, setLocalMaxWR] = useState(filters.max_weekly_return ?? '')

  // 외부에서 filters가 리셋될 때 로컬 상태도 동기화
  useEffect(() => {
    setLocalQ(filters.q || '')
    setLocalMinWR(filters.min_weekly_return ?? '')
    setLocalMaxWR(filters.max_weekly_return ?? '')
  }, [filters.q, filters.min_weekly_return, filters.max_weekly_return])

  const handleSearch = (e) => {
    e.preventDefault()
    const minWR = localMinWR !== '' ? parseFloat(localMinWR) : undefined
    const maxWR = localMaxWR !== '' ? parseFloat(localMaxWR) : undefined
    onFilterChange({
      q: localQ || undefined,
      min_weekly_return: minWR !== undefined && !isNaN(minWR) ? minWR : undefined,
      max_weekly_return: maxWR !== undefined && !isNaN(maxWR) ? maxWR : undefined,
    })
  }

  const handleReset = () => {
    setLocalQ('')
    setLocalMinWR('')
    setLocalMaxWR('')
    onReset()
  }

  const applyNumberFilter = (key, value) => {
    const str = value !== undefined && value !== null ? String(value).trim() : ''
    const parsed = str !== '' ? parseFloat(str) : undefined
    if (str !== '' && isNaN(parsed)) return // NaN 무시
    if (key === 'min_weekly_return') setLocalMinWR(str === '' ? '' : parsed)
    if (key === 'max_weekly_return') setLocalMaxWR(str === '' ? '' : parsed)
    onFilterChange({ [key]: parsed })
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4 mb-4 transition-colors">
      <form onSubmit={handleSearch} className="space-y-4">
        {/* 시장 탭 */}
        <div>
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1.5">시장</label>
          <div className="flex gap-1 bg-gray-100 dark:bg-gray-700 rounded-lg p-0.5 w-fit">
            {MARKET_TABS.map((tab) => (
              <button
                key={tab.value}
                type="button"
                onClick={() => onFilterChange({ market: tab.value })}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                  (filters.market || 'ETF') === tab.value
                    ? 'bg-white dark:bg-gray-600 text-primary-600 dark:text-primary-400 shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* 검색 입력 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            종목 검색
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={localQ}
              onChange={(e) => setLocalQ(e.target.value)}
              placeholder="종목명 또는 코드 입력..."
              className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
            />
            <button type="submit" className="btn btn-primary btn-sm">
              검색
            </button>
          </div>
        </div>

        {/* 필터 행 */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {/* 주간수익률 범위 */}
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">주간수익률 (최소 %)</label>
            <input
              type="number"
              step="0.1"
              value={localMinWR}
              onChange={(e) => setLocalMinWR(e.target.value)}
              onBlur={(e) => applyNumberFilter('min_weekly_return', e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  applyNumberFilter('min_weekly_return', e.target.value)
                }
              }}
              placeholder="예: -5"
              className="w-full px-2 py-1.5 border border-gray-300 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-1 focus:ring-primary-500 transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">주간수익률 (최대 %)</label>
            <input
              type="number"
              step="0.1"
              value={localMaxWR}
              onChange={(e) => setLocalMaxWR(e.target.value)}
              onBlur={(e) => applyNumberFilter('max_weekly_return', e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  applyNumberFilter('max_weekly_return', e.target.value)
                }
              }}
              placeholder="예: 10"
              className="w-full px-2 py-1.5 border border-gray-300 dark:border-gray-600 rounded text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-1 focus:ring-primary-500 transition-colors"
            />
          </div>

          {/* 토글 */}
          <div className="flex flex-col justify-end">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={!!filters.foreign_net_positive}
                onChange={(e) => onFilterChange({ foreign_net_positive: e.target.checked ? true : undefined })}
                className="w-4 h-4 text-primary-500 bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">외국인 순매수</span>
            </label>
          </div>
          <div className="flex flex-col justify-end">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={!!filters.institutional_net_positive}
                onChange={(e) => onFilterChange({ institutional_net_positive: e.target.checked ? true : undefined })}
                className="w-4 h-4 text-primary-500 bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 rounded focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">기관 순매수</span>
            </label>
          </div>
        </div>

        {/* 하단: 초기화 + 갱신 시각 */}
        <div className="flex items-center justify-between">
          <button type="button" onClick={handleReset} className="btn btn-outline btn-sm text-gray-500">
            초기화
          </button>
          {lastUpdated && (
            <span className="text-xs text-gray-400 dark:text-gray-500">
              데이터 갱신: {new Date(lastUpdated).toLocaleString('ko-KR')}
            </span>
          )}
        </div>
      </form>
    </div>
  )
}
