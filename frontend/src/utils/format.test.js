import { describe, it, expect } from 'vitest'
import {
  formatNumber,
  formatVolume,
  formatPrice,
  formatPercent,
  getPriceChangeColor,
  getPriceChangeColorHex,
} from './format'

describe('formatNumber', () => {
  it('숫자를 천 단위 콤마로 포맷팅한다', () => {
    expect(formatNumber(1000)).toBe('1,000')
    expect(formatNumber(1000000)).toBe('1,000,000')
    expect(formatNumber(123456789)).toBe('123,456,789')
  })

  it('소수점을 포함한 숫자를 포맷팅한다', () => {
    expect(formatNumber(1000.5)).toBe('1,000.5')
    expect(formatNumber(1234567.89)).toBe('1,234,567.89')
  })

  it('null 값을 처리한다', () => {
    expect(formatNumber(null)).toBe('-')
  })

  it('undefined 값을 처리한다', () => {
    expect(formatNumber(undefined)).toBe('-')
  })

  it('NaN 값을 처리한다', () => {
    expect(formatNumber(NaN)).toBe('-')
  })

  it('0을 올바르게 포맷팅한다', () => {
    expect(formatNumber(0)).toBe('0')
  })

  it('음수를 올바르게 포맷팅한다', () => {
    expect(formatNumber(-1000)).toBe('-1,000')
    expect(formatNumber(-1234567)).toBe('-1,234,567')
  })
})

describe('formatVolume', () => {
  it('백만 단위 거래량을 M으로 포맷팅한다', () => {
    expect(formatVolume(1000000)).toBe('1.0M')
    expect(formatVolume(2500000)).toBe('2.5M')
    expect(formatVolume(10000000)).toBe('10.0M')
  })

  it('천 단위 거래량을 K로 포맷팅한다', () => {
    expect(formatVolume(1000)).toBe('1.0K')
    expect(formatVolume(5500)).toBe('5.5K')
    expect(formatVolume(999999)).toBe('1000.0K')
  })

  it('천 미만 거래량을 그대로 표시한다', () => {
    expect(formatVolume(100)).toBe('100')
    expect(formatVolume(999)).toBe('999')
  })

  it('null 값을 처리한다', () => {
    expect(formatVolume(null)).toBe('-')
  })

  it('undefined 값을 처리한다', () => {
    expect(formatVolume(undefined)).toBe('-')
  })

  it('NaN 값을 처리한다', () => {
    expect(formatVolume(NaN)).toBe('-')
  })

  it('0을 올바르게 포맷팅한다', () => {
    expect(formatVolume(0)).toBe('0')
  })
})

describe('formatPrice', () => {
  it('가격을 천 단위 콤마로 포맷팅한다', () => {
    expect(formatPrice(15000)).toBe('15,000')
    expect(formatPrice(1234567)).toBe('1,234,567')
  })

  it('소수점을 포함한 가격을 포맷팅한다', () => {
    expect(formatPrice(15000.5)).toBe('15,000.5')
    expect(formatPrice(1234.56)).toBe('1,234.56')
  })

  it('소수점이 없는 경우 소수점을 표시하지 않는다', () => {
    expect(formatPrice(15000)).toBe('15,000')
  })

  it('null 값을 처리한다', () => {
    expect(formatPrice(null)).toBe('-')
  })

  it('undefined 값을 처리한다', () => {
    expect(formatPrice(undefined)).toBe('-')
  })

  it('NaN 값을 처리한다', () => {
    expect(formatPrice(NaN)).toBe('-')
  })

  it('0을 올바르게 포맷팅한다', () => {
    expect(formatPrice(0)).toBe('0')
  })
})

describe('formatPercent', () => {
  it('양수 등락률을 + 부호와 함께 포맷팅한다', () => {
    expect(formatPercent(1.5)).toBe('+1.50%')
    expect(formatPercent(10.23)).toBe('+10.23%')
  })

  it('음수 등락률을 - 부호와 함께 포맷팅한다', () => {
    expect(formatPercent(-1.5)).toBe('-1.50%')
    expect(formatPercent(-10.23)).toBe('-10.23%')
  })

  it('0을 올바르게 포맷팅한다', () => {
    expect(formatPercent(0)).toBe('0.00%')
  })

  it('소수점 둘째 자리까지 표시한다', () => {
    expect(formatPercent(1.234)).toBe('+1.23%')
    expect(formatPercent(-5.678)).toBe('-5.68%')
  })

  it('null 값을 처리한다', () => {
    expect(formatPercent(null)).toBe('-')
  })

  it('undefined 값을 처리한다', () => {
    expect(formatPercent(undefined)).toBe('-')
  })

  it('NaN 값을 처리한다', () => {
    expect(formatPercent(NaN)).toBe('-')
  })
})

describe('getPriceChangeColor', () => {
  it('양수일 때 빨간색 클래스를 반환한다', () => {
    expect(getPriceChangeColor(1.5)).toBe('text-red-600')
    expect(getPriceChangeColor(0.01)).toBe('text-red-600')
  })

  it('음수일 때 파란색 클래스를 반환한다', () => {
    expect(getPriceChangeColor(-1.5)).toBe('text-blue-600')
    expect(getPriceChangeColor(-0.01)).toBe('text-blue-600')
  })

  it('0일 때 회색 클래스를 반환한다', () => {
    expect(getPriceChangeColor(0)).toBe('text-gray-500')
  })

  it('null 값을 처리한다', () => {
    expect(getPriceChangeColor(null)).toBe('text-gray-500')
  })

  it('undefined 값을 처리한다', () => {
    expect(getPriceChangeColor(undefined)).toBe('text-gray-500')
  })

  it('NaN 값을 처리한다', () => {
    expect(getPriceChangeColor(NaN)).toBe('text-gray-500')
  })
})

describe('getPriceChangeColorHex', () => {
  it('양수일 때 빨간색 hex 값을 반환한다', () => {
    expect(getPriceChangeColorHex(1.5)).toBe('#dc2626')
    expect(getPriceChangeColorHex(0.01)).toBe('#dc2626')
  })

  it('음수일 때 파란색 hex 값을 반환한다', () => {
    expect(getPriceChangeColorHex(-1.5)).toBe('#2563eb')
    expect(getPriceChangeColorHex(-0.01)).toBe('#2563eb')
  })

  it('0일 때 회색 hex 값을 반환한다', () => {
    expect(getPriceChangeColorHex(0)).toBe('#6b7280')
  })

  it('null 값을 처리한다', () => {
    expect(getPriceChangeColorHex(null)).toBe('#6b7280')
  })

  it('undefined 값을 처리한다', () => {
    expect(getPriceChangeColorHex(undefined)).toBe('#6b7280')
  })

  it('NaN 값을 처리한다', () => {
    expect(getPriceChangeColorHex(NaN)).toBe('#6b7280')
  })
})
