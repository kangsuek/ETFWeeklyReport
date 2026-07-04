import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { renderWithProviders, screen, fireEvent } from '../../test/utils'
import { server } from '../../test/mocks/server'
import UptrendWatchlistCheck from './UptrendWatchlistCheck'

const BASE = '*/api'

describe('UptrendWatchlistCheck', () => {
  it('점검 전에는 결과가 없다', () => {
    renderWithProviders(<UptrendWatchlistCheck />)
    expect(screen.getByText('일괄 점검')).toBeInTheDocument()
    expect(screen.queryByText(/총 .*종목 점검/)).not.toBeInTheDocument()
  })

  it('점검하면 확정·대기 종목만 강조 표시한다', async () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend/watchlist`, () => HttpResponse.json({
        items: [
          { ticker: '005930', name: '삼성전자', status: 'confirmed', latest: { confirmed_date: '2026-07-01', confirm_path: 'hold' } },
          { ticker: '000660', name: 'SK하이닉스', status: 'pending', latest: { status: 'pending' } },
          { ticker: '035720', name: '카카오', status: 'none', latest: null },
          { ticker: '068270', name: '셀트리온', status: 'insufficient_data', latest: null },
        ],
      })),
    )
    renderWithProviders(<UptrendWatchlistCheck />)

    fireEvent.click(screen.getByText('일괄 점검'))

    expect(await screen.findByText('삼성전자')).toBeInTheDocument()
    expect(screen.getByText('SK하이닉스')).toBeInTheDocument()
    // none·insufficient_data는 강조 목록에서 제외
    expect(screen.queryByText('카카오')).not.toBeInTheDocument()
    expect(screen.queryByText('셀트리온')).not.toBeInTheDocument()
    expect(screen.getByText(/총 4종목 점검/)).toBeInTheDocument()
  })

  it('확정·대기가 없으면 안내 문구를 표시한다', async () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend/watchlist`, () => HttpResponse.json({
        items: [
          { ticker: '005930', name: '삼성전자', status: 'none', latest: null },
        ],
      })),
    )
    renderWithProviders(<UptrendWatchlistCheck />)

    fireEvent.click(screen.getByText('일괄 점검'))

    expect(await screen.findByText('현재 상승흐름 확정·대기 종목이 없습니다')).toBeInTheDocument()
  })
})
