import { describe, it, expect } from 'vitest'
import { isWithinRecentDays } from './dateRange'

// 기준일 고정 — 로컬 타임존과 무관하게 날짜 문자열로 비교되어야 한다
const TODAY = new Date(2026, 6, 9) // 2026-07-09 (month는 0-based)

describe('isWithinRecentDays', () => {
  it('오늘 날짜는 포함된다', () => {
    expect(isWithinRecentDays('2026-07-09', 7, TODAY)).toBe(true)
  })

  it('정확히 7일 전은 경계로 포함된다', () => {
    expect(isWithinRecentDays('2026-07-02', 7, TODAY)).toBe(true)
  })

  it('8일 전은 제외된다', () => {
    expect(isWithinRecentDays('2026-07-01', 7, TODAY)).toBe(false)
  })

  it('수개월 전은 제외된다', () => {
    expect(isWithinRecentDays('2026-04-10', 7, TODAY)).toBe(false)
  })

  it('미래 날짜는 포함된다(경계 이상)', () => {
    expect(isWithinRecentDays('2026-07-20', 7, TODAY)).toBe(true)
  })

  it('타임스탬프 접두 문자열도 날짜만 보고 판정한다', () => {
    expect(isWithinRecentDays('2026-07-05T23:59:59', 7, TODAY)).toBe(true)
  })

  it('월 경계를 넘어도 정확하다', () => {
    const firstOfMonth = new Date(2026, 6, 3) // 2026-07-03
    expect(isWithinRecentDays('2026-06-26', 7, firstOfMonth)).toBe(true)
    expect(isWithinRecentDays('2026-06-25', 7, firstOfMonth)).toBe(false)
  })

  it('빈 값·형식 불일치는 false', () => {
    expect(isWithinRecentDays(null, 7, TODAY)).toBe(false)
    expect(isWithinRecentDays(undefined, 7, TODAY)).toBe(false)
    expect(isWithinRecentDays('', 7, TODAY)).toBe(false)
    expect(isWithinRecentDays('not-a-date', 7, TODAY)).toBe(false)
  })
})
