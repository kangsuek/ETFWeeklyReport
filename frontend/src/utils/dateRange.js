/**
 * 날짜 범위 계산 유틸리티
 * 초기 날짜 범위를 즉시 계산하여 API 호출 지연 방지
 */
import { subDays, subMonths, subYears, startOfYear, format } from 'date-fns'

/**
 * 날짜 범위 계산
 * @param {string} range - '7d', '1m', '3m', '6m', 'ytd', '1y'
 * @returns {{ startDate: string, endDate: string, range: string }}
 */
export function calculateDateRange(range = '7d') {
  const today = new Date()
  let calculatedStartDate

  switch (range) {
    case '7d':
      calculatedStartDate = subDays(today, 7)
      break
    case '1m':
      calculatedStartDate = subMonths(today, 1)
      break
    case '3m':
      calculatedStartDate = subMonths(today, 3)
      break
    case '6m':
      calculatedStartDate = subMonths(today, 6)
      break
    case 'ytd':
      calculatedStartDate = startOfYear(today)
      break
    case '1y':
      calculatedStartDate = subYears(today, 1)
      break
    default:
      calculatedStartDate = subDays(today, 7)
  }

  return {
    startDate: format(calculatedStartDate, 'yyyy-MM-dd'),
    endDate: format(today, 'yyyy-MM-dd'),
    range
  }
}

/**
 * ISO 날짜 문자열이 최근 N일 이내인지 판정한다.
 *
 * 타임존 오차를 피하려고 Date 연산 대신 `YYYY-MM-DD` 문자열을 비교한다
 * (ISO 날짜는 사전순 비교가 곧 시간순 비교).
 *
 * @param {string} iso - 'YYYY-MM-DD' 또는 그 접두를 가진 문자열
 * @param {number} days - 며칠 이내인지 (오늘 기준, 경계 포함)
 * @param {Date} [today] - 기준일 (테스트 주입용)
 * @returns {boolean} 유효하지 않은 값이면 false
 */
export function isWithinRecentDays(iso, days, today = new Date()) {
  if (!iso) return false
  const target = String(iso).slice(0, 10)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(target)) return false
  const cutoff = format(subDays(today, days), 'yyyy-MM-dd')
  return target >= cutoff
}
