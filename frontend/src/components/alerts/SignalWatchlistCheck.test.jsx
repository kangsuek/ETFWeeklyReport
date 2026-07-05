import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { renderWithProviders, screen, fireEvent } from '../../test/utils'
import { server } from '../../test/mocks/server'
import SignalWatchlistCheck from './SignalWatchlistCheck'

const BASE = '*/api'

describe('SignalWatchlistCheck', () => {
  it('down 방향은 downtrend watchlist를 조회해 확정·대기만 강조한다', async () => {
    server.use(
      http.get(`${BASE}/alerts/downtrend/watchlist`, () => HttpResponse.json({
        items: [
          { ticker: '005930', name: '삼성전자', status: 'confirmed', latest: { confirmed_date: '2026-07-01' } },
          { ticker: '000660', name: 'SK하이닉스', status: 'pending', latest: { status: 'pending' } },
          { ticker: '035720', name: '카카오', status: 'none', latest: null },
        ],
      })),
    )
    renderWithProviders(<SignalWatchlistCheck direction="down" />)

    fireEvent.click(screen.getByText('일괄 점검'))

    expect(await screen.findByText('삼성전자')).toBeInTheDocument()
    expect(screen.getByText('SK하이닉스')).toBeInTheDocument()
    expect(screen.queryByText('카카오')).not.toBeInTheDocument()
    expect(screen.getByText('관심종목 하락흐름 점검')).toBeInTheDocument()
  })

  it('확정·대기가 없으면 안내 문구를 표시한다', async () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend/watchlist`, () => HttpResponse.json({
        items: [{ ticker: '005930', name: '삼성전자', status: 'none', latest: null }],
      })),
    )
    renderWithProviders(<SignalWatchlistCheck direction="up" />)

    fireEvent.click(screen.getByText('일괄 점검'))
    expect(await screen.findByText('현재 상승흐름 확정·대기 종목이 없습니다')).toBeInTheDocument()
  })
})
