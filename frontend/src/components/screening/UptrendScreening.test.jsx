import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { renderWithProviders, screen } from '../../test/utils'
import { server } from '../../test/mocks/server'
import UptrendScreening from './UptrendScreening'

const BASE = '*/api'

describe('UptrendScreening', () => {
  it('확정·대기 종목만 표시하고 none/데이터부족은 제외한다', async () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend/watchlist`, () => HttpResponse.json({
        items: [
          { ticker: '161890', name: '한국콜마', status: 'confirmed', latest: { confirmed_date: '2026-07-01', breakout_level: 55000, confirm_path: 'hold' } },
          { ticker: '000660', name: 'SK하이닉스', status: 'pending', latest: { breakout_date: '2026-07-02', breakout_level: 240000 } },
          { ticker: '005930', name: '삼성전자', status: 'none', latest: null },
          { ticker: '068270', name: '셀트리온', status: 'insufficient_data', latest: null },
        ],
      })),
    )
    renderWithProviders(<UptrendScreening />)

    expect(await screen.findByText('한국콜마')).toBeInTheDocument()
    expect(screen.getByText('SK하이닉스')).toBeInTheDocument()
    expect(screen.queryByText('삼성전자')).not.toBeInTheDocument()
    expect(screen.queryByText('셀트리온')).not.toBeInTheDocument()
    // 요약 카운트
    expect(screen.getByText(/확정 1/)).toBeInTheDocument()
    expect(screen.getByText(/대기 1/)).toBeInTheDocument()
    // 돌파선 포맷(천 단위 콤마)
    expect(screen.getByText('55,000원')).toBeInTheDocument()
  })

  it('확정·대기가 없으면 안내 문구를 표시한다', async () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend/watchlist`, () => HttpResponse.json({
        items: [{ ticker: '005930', name: '삼성전자', status: 'none', latest: null }],
      })),
    )
    renderWithProviders(<UptrendScreening />)

    expect(await screen.findByText('현재 상승흐름 확정·대기 종목이 없습니다')).toBeInTheDocument()
  })

  it('확정이 대기보다 먼저 정렬된다', async () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend/watchlist`, () => HttpResponse.json({
        items: [
          { ticker: '000660', name: 'SK하이닉스', status: 'pending', latest: { breakout_date: '2026-07-02', breakout_level: 240000 } },
          { ticker: '161890', name: '한국콜마', status: 'confirmed', latest: { confirmed_date: '2026-07-01', breakout_level: 55000 } },
        ],
      })),
    )
    renderWithProviders(<UptrendScreening />)

    const rows = await screen.findAllByRole('row')
    // rows[0]은 헤더, rows[1]이 첫 데이터 행 → 확정(한국콜마)이 먼저
    expect(rows[1]).toHaveTextContent('한국콜마')
    expect(rows[2]).toHaveTextContent('SK하이닉스')
  })
})
