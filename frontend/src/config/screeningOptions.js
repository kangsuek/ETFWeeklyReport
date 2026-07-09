// 조건검색 필터/정렬 옵션 — 필터 UI와 흐름 배치 점검의 조건 칩이 함께 쓴다.
export const MARKET_TABS = [
  { value: 'ETF', label: 'ETF' },
  { value: 'KOSPI', label: 'KOSPI' },
  { value: 'KOSDAQ', label: 'KOSDAQ' },
  { value: 'ALL', label: '전체' },
]

export const SORT_OPTIONS = [
  { value: 'weekly_return', label: '주간수익률' },
  { value: 'daily_change_pct', label: '등락률' },
  { value: 'volume', label: '거래량' },
  { value: 'close_price', label: '현재가' },
  { value: 'foreign_net', label: '외국인' },
  { value: 'institutional_net', label: '기관' },
  { value: 'name', label: '종목명' },
]

const labelOf = (options, value, fallback) =>
  options.find((o) => o.value === value)?.label ?? fallback

/**
 * 현재 조건검색 필터를 사람이 읽는 칩 목록으로 요약한다.
 * (배치 점검이 어떤 조건으로 종목을 고르는지 화면에 그대로 보여주기 위함)
 */
export function describeFilters(filters = {}) {
  const chips = []
  const market = filters.market || 'ETF'
  chips.push({ key: 'market', label: labelOf(MARKET_TABS, market, market) })

  if (filters.q) chips.push({ key: 'q', label: `"${filters.q}"` })
  if (filters.sector) chips.push({ key: 'sector', label: filters.sector })
  if (filters.min_weekly_return !== undefined) {
    chips.push({ key: 'minWr', label: `주간수익률 ≥ ${filters.min_weekly_return}%` })
  }
  if (filters.max_weekly_return !== undefined) {
    chips.push({ key: 'maxWr', label: `주간수익률 ≤ ${filters.max_weekly_return}%` })
  }
  if (filters.foreign_net_positive) chips.push({ key: 'fn', label: '외국인 순매수' })
  if (filters.institutional_net_positive) chips.push({ key: 'in', label: '기관 순매수' })

  return chips
}

/** 정렬 기준·방향을 "주간수익률 내림차순" 형태로 요약. */
export function describeSort(filters = {}) {
  const by = labelOf(SORT_OPTIONS, filters.sort_by, filters.sort_by ?? '주간수익률')
  const dir = filters.sort_dir === 'asc' ? '오름차순' : '내림차순'
  return `${by} ${dir}`
}
