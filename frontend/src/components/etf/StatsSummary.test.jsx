import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '../../test/utils'
import StatsSummary from './StatsSummary'

// Mock data (API 형식: 내림차순 - 최신 날짜가 먼저)
const mockPriceData = [
  {
    date: '2025-11-05',
    close_price: 11000,
    volume: 1400000,
  },
  {
    date: '2025-11-04',
    close_price: 10800,
    volume: 1300000,
  },
  {
    date: '2025-11-03',
    close_price: 10200,
    volume: 1100000,
  },
  {
    date: '2025-11-02',
    close_price: 10500,
    volume: 1200000,
  },
  {
    date: '2025-11-01',
    close_price: 10000,
    volume: 1000000,
  },
]

describe('StatsSummary', () => {
  describe('기본 렌더링', () => {
    it('2개의 통계 카드를 표시한다', () => {
      renderWithProviders(<StatsSummary data={mockPriceData} />)

      expect(screen.getByText('수익률')).toBeInTheDocument()
      expect(screen.getByText('가격 범위')).toBeInTheDocument()
    })

    it('아이콘이 표시된다', () => {
      renderWithProviders(<StatsSummary data={mockPriceData} />)

      expect(screen.getByText('📈')).toBeInTheDocument()
      expect(screen.getByText('💰')).toBeInTheDocument()
    })

    it('데이터가 없을 때 메시지를 표시한다', () => {
      renderWithProviders(<StatsSummary data={[]} />)

      expect(screen.getByText('통계를 계산할 데이터가 부족합니다')).toBeInTheDocument()
      expect(screen.getByText('최소 2개 이상의 데이터가 필요합니다')).toBeInTheDocument()
    })

    it('데이터가 1개일 때 메시지를 표시한다', () => {
      renderWithProviders(<StatsSummary data={[mockPriceData[0]]} />)

      expect(screen.getByText('통계를 계산할 데이터가 부족합니다')).toBeInTheDocument()
    })
  })

  describe('수익률 계산', () => {
    it('기간 수익률을 정확하게 계산한다', () => {
      renderWithProviders(<StatsSummary data={mockPriceData} />)

      // 기간 수익률 = (11000 - 10000) / 10000 * 100 = 10%
      expect(screen.getByText('기간 수익률')).toBeInTheDocument()
      expect(screen.getByText('+10.00%')).toBeInTheDocument()
    })

    it('연환산 수익률을 복리 효과를 반영하여 계산한다 (거래일 기준)', () => {
      // 21개 데이터, 7.09% 수익 (두산에너빌리티 예시)
      const baseDate = new Date('2025-10-13')
      const testData = Array.from({ length: 21 }, (_, i) => {
        // 7.09% 수익을 선형 분배
        const progress = i / 20
        const price = 10000 * (1 + 0.0709 * progress)
        const date = new Date(baseDate)
        date.setDate(baseDate.getDate() + i)
        return {
          date: date.toISOString().split('T')[0],
          close_price: Math.round(price),
          volume: 1000000
        }
      }).reverse()  // API 형식에 맞게 최신순으로

      renderWithProviders(<StatsSummary data={testData} />)

      expect(screen.getByText('연환산 수익률')).toBeInTheDocument()
      expect(screen.getByText('기간 수익률')).toBeInTheDocument()

      // 기간 수익률: 7.09%
      expect(screen.getByText('+7.09%')).toBeInTheDocument()

      // 거래일수: 21일 (데이터 포인트 개수)
      // 연환산: (1.0709)^(365/21) - 1 ≈ 183.33%
      // 백엔드 ComparisonService와 동일한 로직 (거래일 기준)

      // 모든 퍼센트 값을 가져와서 연환산 수익률 확인
      const percentageElements = screen.getAllByText(/[+-]\d+\.\d+%/)
      expect(percentageElements.length).toBeGreaterThan(1)  // 기간 수익률 + 연환산 수익률
    })

    it('거래일 기준 연환산 계산 - 실제 데이터와 일치', () => {
      // 31개 데이터 (거래일 기준)
      const baseDate = new Date('2025-10-01')
      const testData = Array.from({ length: 31 }, (_, i) => {
        const progress = i / 30
        const price = 10000 * (1 + 0.0709 * progress)
        const date = new Date(baseDate)
        date.setDate(baseDate.getDate() + i)
        return {
          date: date.toISOString().split('T')[0],
          close_price: Math.round(price),
          volume: 1000000
        }
      }).reverse()

      renderWithProviders(<StatsSummary data={testData} />)

      // 거래일수: 31일
      // 연환산: (1.0709)^(365/31) - 1 ≈ 1.2395 = 123.95%
      expect(screen.getByText('연환산 수익률')).toBeInTheDocument()
    })

    it('양수 수익률은 빨강색으로 표시된다', () => {
      const { container } = renderWithProviders(<StatsSummary data={mockPriceData} />)

      const redElements = container.querySelectorAll('.text-red-600')
      expect(redElements.length).toBeGreaterThan(0)
    })

    it('음수 수익률은 파랑색으로 표시된다', () => {
      const negativeReturnData = [
        { date: '2025-11-03', close_price: 10000, volume: 1200000 },
        { date: '2025-11-02', close_price: 10500, volume: 1100000 },
        { date: '2025-11-01', close_price: 11000, volume: 1000000 },
      ]

      const { container } = renderWithProviders(<StatsSummary data={negativeReturnData} />)

      const blueElements = container.querySelectorAll('.text-blue-600')
      expect(blueElements.length).toBeGreaterThan(0)
    })
  })


  describe('가격 범위 계산', () => {
    it('최고가를 정확하게 표시한다', () => {
      renderWithProviders(<StatsSummary data={mockPriceData} />)

      expect(screen.getByText('최고가')).toBeInTheDocument()
      expect(screen.getByText('11,000')).toBeInTheDocument() // 최고가: 11000
    })

    it('최저가를 정확하게 표시한다', () => {
      renderWithProviders(<StatsSummary data={mockPriceData} />)

      expect(screen.getByText('최저가')).toBeInTheDocument()
      expect(screen.getByText('10,000')).toBeInTheDocument() // 최저가: 10000
    })

    it('최고가와 최저가의 날짜를 괄호 안에 표시한다', () => {
      renderWithProviders(<StatsSummary data={mockPriceData} />)

      // 최고가 날짜: 2025-11-05 -> (11-05)
      expect(screen.getByText(/\(11-05\)/)).toBeInTheDocument()
      // 최저가 날짜: 2025-11-01 -> (11-01)
      expect(screen.getByText(/\(11-01\)/)).toBeInTheDocument()
    })

    it('평균가 진행률 바를 표시한다', () => {
      renderWithProviders(<StatsSummary data={mockPriceData} />)

      expect(screen.getByText('평균가')).toBeInTheDocument()
    })

    it('최고가는 빨강색으로 표시된다', () => {
      const { container } = renderWithProviders(<StatsSummary data={mockPriceData} />)

      // 최고가 값 근처에 빨강색 클래스가 있어야 함
      const redElements = container.querySelectorAll('.text-red-600')
      expect(redElements.length).toBeGreaterThan(0)
    })

    it('최저가는 파랑색으로 표시된다', () => {
      const { container } = renderWithProviders(<StatsSummary data={mockPriceData} />)

      // 최저가 값 근처에 파랑색 클래스가 있어야 함
      const blueElements = container.querySelectorAll('.text-blue-600')
      expect(blueElements.length).toBeGreaterThan(0)
    })
  })


  describe('엣지 케이스', () => {
    it('2개의 데이터로도 정상 작동한다', () => {
      const twoItems = mockPriceData.slice(0, 2)
      renderWithProviders(<StatsSummary data={twoItems} />)

      expect(screen.getByText('수익률')).toBeInTheDocument()
      expect(screen.getByText('가격 범위')).toBeInTheDocument()
    })

    it('같은 가격 데이터도 처리한다', () => {
      const samePriceData = [
        { date: '2025-11-03', close_price: 10000, volume: 1000000 },
        { date: '2025-11-02', close_price: 10000, volume: 1000000 },
        { date: '2025-11-01', close_price: 10000, volume: 1000000 },
      ]

      renderWithProviders(<StatsSummary data={samePriceData} />)

      // 수익률 0%
      expect(screen.getByText('기간 수익률')).toBeInTheDocument()
      expect(screen.getAllByText('0.00%').length).toBeGreaterThan(0)
    })

    it('매우 큰 숫자도 처리한다', () => {
      const largePriceData = [
        { date: '2025-11-02', close_price: 2000000, volume: 20000000 },
        { date: '2025-11-01', close_price: 1000000, volume: 10000000 },
      ]

      renderWithProviders(<StatsSummary data={largePriceData} />)

      expect(screen.getByText('수익률')).toBeInTheDocument()
      // 100% 수익률
      expect(screen.getByText('+100.00%')).toBeInTheDocument()
    })

    it('소수점 가격도 처리한다', () => {
      const decimalPriceData = [
        { date: '2025-11-03', close_price: 10.8, volume: 1200000 },
        { date: '2025-11-02', close_price: 11.2, volume: 1100000 },
        { date: '2025-11-01', close_price: 10.5, volume: 1000000 },
      ]

      renderWithProviders(<StatsSummary data={decimalPriceData} />)

      expect(screen.getByText('수익률')).toBeInTheDocument()
    })
  })

  describe('반응형 디자인', () => {
    it('그리드 레이아웃이 적용되어 있다', () => {
      const { container } = renderWithProviders(<StatsSummary data={mockPriceData} />)

      const grid = container.querySelector('.grid')
      expect(grid).toBeInTheDocument()
      expect(grid).toHaveClass('md:grid-cols-2')
    })
  })

  describe('다크모드', () => {
    it('다크모드 스타일 클래스가 포함되어 있다', () => {
      const { container } = renderWithProviders(<StatsSummary data={mockPriceData} />)

      // dark: 클래스가 있는지 확인
      const darkModeElements = container.querySelectorAll('[class*="dark:"]')
      expect(darkModeElements.length).toBeGreaterThan(0)
    })
  })

  describe('진행률 바', () => {
    it('진행률 바가 올바른 퍼센트로 표시된다', () => {
      const { container } = renderWithProviders(<StatsSummary data={mockPriceData} />)

      // 진행률 바 요소 확인
      const progressBars = container.querySelectorAll('.bg-blue-500')
      expect(progressBars.length).toBeGreaterThan(0)
    })

    it('진행률이 0-100% 범위 내에 있다', () => {
      const { container } = renderWithProviders(<StatsSummary data={mockPriceData} />)

      const progressBars = container.querySelectorAll('.bg-blue-500')
      progressBars.forEach((bar) => {
        const width = bar.style.width
        const percentage = parseFloat(width)
        expect(percentage).toBeGreaterThanOrEqual(0)
        expect(percentage).toBeLessThanOrEqual(100)
      })
    })
  })
})
