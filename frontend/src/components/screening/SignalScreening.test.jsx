import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { renderWithProviders, screen, waitFor, fireEvent } from '../../test/utils'
import { server } from '../../test/mocks/server'
import SignalScreening from './SignalScreening'

const BASE = '*/api'

/** 오늘 기준 N일 전 'YYYY-MM-DD' — 시간이 지나도 안 깨지는 픽스처용 */
const isoDaysAgo = (daysAgo) => {
  const d = new Date()
  d.setDate(d.getDate() - daysAgo)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

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
  it('확정/돌파일이 7일을 넘은 신호는 제외하고 경과 건수를 알린다', async () => {
    const iso = isoDaysAgo
    server.use(
      http.get(`${BASE}/alerts/uptrend/watchlist`, () => HttpResponse.json({ items: [] })),
      http.get(`${BASE}/scanner`, () =>
        HttpResponse.json({ items: [{ ticker: 'FRESH' }, { ticker: 'OLD' }, { ticker: 'EDGE' }], total: 3 })),
      http.post(`${BASE}/alerts/signals/scan-batch`, () => HttpResponse.json({
        items: [
          { ticker: 'FRESH', name: '최근확정', status: 'confirmed', latest: { confirmed_date: iso(2), breakout_level: 100 } },
          { ticker: 'EDGE', name: '경계대기', status: 'pending', latest: { breakout_date: iso(7), breakout_level: 200 } },
          { ticker: 'OLD', name: '지난확정', status: 'confirmed', latest: { confirmed_date: iso(20), breakout_level: 300 } },
        ],
        scanned: 3,
      })),
    )
    renderWithProviders(<SignalScreening direction="up" filters={{}} />)

    fireEvent.click(screen.getByText('조건검색 결과'))
    fireEvent.click(screen.getByText('점검 실행'))

    expect(await screen.findByText('최근확정')).toBeInTheDocument()
    expect(screen.getByText('경계대기')).toBeInTheDocument()   // 정확히 7일 전 → 경계 포함
    expect(screen.queryByText('지난확정')).not.toBeInTheDocument()
    expect(screen.getByText(/7일 경과 제외 1/)).toBeInTheDocument()
    expect(screen.getByText(/확정 1/)).toBeInTheDocument()
    expect(screen.getByText(/대기 1/)).toBeInTheDocument()
  })

  it('관심종목 모드에는 7일 필터를 적용하지 않는다', async () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend/watchlist`, () => HttpResponse.json({
        items: [
          { ticker: 'OLD', name: '오래된확정', status: 'confirmed', latest: { confirmed_date: '2026-01-01', breakout_level: 300 } },
        ],
      })),
    )
    renderWithProviders(<SignalScreening direction="up" filters={{}} />)

    expect(await screen.findByText('오래된확정')).toBeInTheDocument()
  })

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
            // 최근 7일 필터에 걸리지 않도록 상대 날짜(어제)를 쓴다
            { ticker: 'AAA', name: '가나다', status: 'confirmed', latest: { confirmed_date: isoDaysAgo(1), breakout_level: 1234 } },
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
