import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ETFCardGrid from './ETFCardGrid'

// Mock ETFCard
vi.mock('../etf/ETFCard', () => ({
  default: ({ etf, compactMode }) => (
    <div data-testid={`etf-card-${etf.ticker}`}>
      {etf.name} {compactMode && '(compact)'}
    </div>
  )
}))

describe('ETFCardGrid', () => {
  const mockETFs = [
    {
      ticker: '069660',
      name: 'KODEX 반도체',
      type: 'ETF',
      theme: '반도체',
    },
    {
      ticker: '114800',
      name: 'KODEX 인버스',
      type: 'ETF',
      theme: '인버스',
    },
  ]

  it('ETF 카드들을 그리드로 표시한다', () => {
    render(<ETFCardGrid etfs={mockETFs} />)

    expect(screen.getByTestId('etf-card-069660')).toBeInTheDocument()
    expect(screen.getByTestId('etf-card-114800')).toBeInTheDocument()
  })

  it('compactMode가 true일 때 컴팩트 모드를 적용한다', () => {
    render(<ETFCardGrid etfs={mockETFs} compactMode={true} />)

    expect(screen.getByText('KODEX 반도체 (compact)')).toBeInTheDocument()
  })

  it('빈 배열일 때도 렌더링된다', () => {
    render(<ETFCardGrid etfs={[]} />)

    expect(screen.queryByTestId(/etf-card/)).not.toBeInTheDocument()
  })
})

