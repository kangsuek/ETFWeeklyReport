import { describe, it, expect } from 'vitest'
import { describeFilters, describeSort } from './screeningOptions'

describe('describeFilters', () => {
  it('빈 필터는 기본 시장(ETF) 칩만 만든다', () => {
    expect(describeFilters({})).toEqual([{ key: 'market', label: 'ETF' }])
  })

  it('ALL 시장은 "전체"로 표기한다', () => {
    expect(describeFilters({ market: 'ALL' })[0].label).toBe('전체')
  })

  it('설정된 조건만 칩으로 만든다', () => {
    const chips = describeFilters({
      market: 'KOSPI', q: '반도체', sector: 'IT',
      min_weekly_return: 3, max_weekly_return: 20,
      foreign_net_positive: true,
    })
    expect(chips.map((c) => c.label)).toEqual([
      'KOSPI', '"반도체"', 'IT', '주간수익률 ≥ 3%', '주간수익률 ≤ 20%', '외국인 순매수',
    ])
  })

  it('0%도 유효한 조건으로 취급한다 (undefined만 제외)', () => {
    const labels = describeFilters({ min_weekly_return: 0 }).map((c) => c.label)
    expect(labels).toContain('주간수익률 ≥ 0%')
  })

  it('false인 체크박스는 칩을 만들지 않는다', () => {
    const labels = describeFilters({ foreign_net_positive: false }).map((c) => c.label)
    expect(labels).not.toContain('외국인 순매수')
  })
})

describe('describeSort', () => {
  it('기본값은 주간수익률 내림차순', () => {
    expect(describeSort({})).toBe('주간수익률 내림차순')
  })

  it('정렬 기준 라벨과 방향을 조합한다', () => {
    expect(describeSort({ sort_by: 'volume', sort_dir: 'asc' })).toBe('거래량 오름차순')
    expect(describeSort({ sort_by: 'foreign_net', sort_dir: 'desc' })).toBe('외국인 내림차순')
  })
})
