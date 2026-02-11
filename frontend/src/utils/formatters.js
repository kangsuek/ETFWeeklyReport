/**
 * 공통 포맷팅 유틸리티 (스크리닝, 테마, 추천 등에서 공유)
 */

export function formatPercent(val) {
  if (val == null) return '-'
  const arrow = val > 0 ? '▲' : val < 0 ? '▼' : ''
  const sign = val > 0 ? '+' : ''
  return `${arrow} ${sign}${val.toFixed(2)}%`
}

export function getChangeColor(val) {
  if (val == null) return 'text-gray-500 dark:text-gray-400'
  if (val > 0) return 'text-red-600 dark:text-red-400'
  if (val < 0) return 'text-blue-600 dark:text-blue-400'
  return 'text-gray-500 dark:text-gray-400'
}

export function formatNumber(num) {
  if (num == null) return '-'
  return num.toLocaleString('ko-KR')
}

export function formatSignedNumber(num) {
  if (num == null) return '-'
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toLocaleString('ko-KR')}`
}
