import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { renderWithProviders, screen, waitFor, fireEvent } from '../../test/utils'
import { server } from '../../test/mocks/server'
import SignalScreening from './SignalScreening'

const BASE = '*/api'

const WATCHLIST_ITEMS = [
  { ticker: '161890', name: '한국콜마', status: 'confirmed', latest: { confirmed_date: '2026-07-01', breakout_level: 55000 } },
  { ticker: '000660', name: 'SK하이닉스', status: 'pending', latest: { breakout_date: '2026-07-02', breakout_level: 240000 } },
  { ticker: '005930', name: '삼성전자', status: 'none', latest: null },
]

describe('SignalScreening — 관심종목 모드', () => {
  it('확정·대기만 표시하고 none은 제외한다', async () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend/watchlist`, () =>
        HttpResponse.json({ items: WATCHLIST_ITEMS })),
    )
    renderWithProviders(<SignalScreening direction="up" />)

    expect(await screen.findByText('한국콜마')).toBeInTheDocument()
    expect(screen.getByText('SK하이닉스')).toBeInTheDocument()
    expect(screen.queryByText('삼성전자')).not.toBeInTheDocument()
    expect(screen.getByText('55,000원')).toBeInTheDocument()
  })
})

describe('SignalScreening — 조건검색 모드 (배치 점검)', () => {
  it('조건검색 결과를 상위 N개로 조회해 배치 점검한다', async () => {
    let searchPageSize = null
    let batchBody = null
    server.use(
      http.get(`${BASE}/alerts/uptrend/watchlist`, () => HttpResponse.json({ items: [] })),
      http.get(`${BASE}/scanner`, ({ request }) => {
        searchPageSize = new URL(request.url).searchParams.get('page_size')
        return HttpResponse.json({
          items: [{ ticker: 'AAA' }, { ticker: 'BBB' }], total: 2, page: 1, page_size: 2,
        })
      }),
      http.post(`${BASE}/alerts/signals/scan-batch`, async ({ request }) => {
        batchBody = await request.json()
        return HttpResponse.json({
          items: [
            { ticker: 'AAA', name: '가나다', status: 'confirmed', latest: { confirmed_date: '2026-07-03', breakout_level: 1234 } },
            { ticker: 'BBB', name: '라마바', status: 'insufficient_data', latest: null },
          ],
          scanned: 2,
        })
      }),
    )
    renderWithProviders(<SignalScreening direction="up" filters={{ market: 'ETF', sort_by: 'weekly_return' }} />)

    fireEvent.click(screen.getByText('조건검색 결과'))
    fireEvent.change(screen.getByLabelText('상위'), { target: { value: '5' } })
    fireEvent.click(screen.getByText('점검 실행'))

    expect(await screen.findByText('가나다')).toBeInTheDocument()
    await waitFor(() => expect(searchPageSize).toBe('5'))
    expect(batchBody).toMatchObject({ tickers: ['AAA', 'BBB'], direction: 'up', limit: 5 })
    // 판정 불가(insufficient_data)는 목록에서 빠지고 요약에만 집계
    expect(screen.queryByText('라마바')).not.toBeInTheDocument()
    expect(screen.getByText(/판정 불가 1/)).toBeInTheDocument()
  })

  it('N 입력은 최대치(50)로 클램프된다', () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend/watchlist`, () => HttpResponse.json({ items: [] })),
    )
    renderWithProviders(<SignalScreening direction="up" filters={{}} />)

    fireEvent.click(screen.getByText('조건검색 결과'))
    const input = screen.getByLabelText('상위')
    fireEvent.change(input, { target: { value: '999' } })

    expect(input).toHaveValue(50)
  })

  it('적용된 조건검색 필터를 칩으로 표시한다', () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend/watchlist`, () => HttpResponse.json({ items: [] })),
    )
    renderWithProviders(
      <SignalScreening
        direction="up"
        filters={{
          market: 'KOSDAQ', sector: '반도체', q: '전력',
          min_weekly_return: 3, foreign_net_positive: true,
          sort_by: 'volume', sort_dir: 'asc',
        }}
      />,
    )

    fireEvent.click(screen.getByText('조건검색 결과'))

    const summary = screen.getByLabelText('적용된 조건검색 필터')
    expect(summary).toHaveTextContent('KOSDAQ')
    expect(summary).toHaveTextContent('반도체')
    expect(summary).toHaveTextContent('"전력"')
    expect(summary).toHaveTextContent('주간수익률 ≥ 3%')
    expect(summary).toHaveTextContent('외국인 순매수')
    expect(summary).toHaveTextContent('거래량 오름차순 상위 30개')
  })

  it('필터가 비어도 기본값(ETF·주간수익률 내림차순)을 보여준다', () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend/watchlist`, () => HttpResponse.json({ items: [] })),
    )
    renderWithProviders(<SignalScreening direction="up" filters={{}} />)

    fireEvent.click(screen.getByText('조건검색 결과'))

    const summary = screen.getByLabelText('적용된 조건검색 필터')
    expect(summary).toHaveTextContent('ETF')
    expect(summary).toHaveTextContent('주간수익률 내림차순 상위 30개')
  })

  it('실행 전에는 안내 문구를 표시한다', () => {
    server.use(
      http.get(`${BASE}/alerts/downtrend/watchlist`, () => HttpResponse.json({ items: [] })),
    )
    renderWithProviders(<SignalScreening direction="down" filters={{}} />)

    fireEvent.click(screen.getByText('조건검색 결과'))

    expect(screen.getByText(/‘점검 실행’을 누르면/)).toBeInTheDocument()
  })
})
