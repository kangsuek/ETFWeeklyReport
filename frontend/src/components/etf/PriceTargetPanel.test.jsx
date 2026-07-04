import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { renderWithProviders, screen, waitFor, fireEvent } from '../../test/utils'
import { server } from '../../test/mocks/server'
import PriceTargetPanel from './PriceTargetPanel'

const BASE = '*/api'

describe('PriceTargetPanel — 상승흐름 탭', () => {
  it('규칙이 없으면 토글이 OFF로 표시된다', async () => {
    server.use(
      http.get(`${BASE}/alerts/:ticker`, () => HttpResponse.json([])),
      http.get(`${BASE}/alerts/signals/:ticker`, () => HttpResponse.json([])),
    )
    renderWithProviders(<PriceTargetPanel ticker="005930" currentPrice={70000} />)

    fireEvent.click(await screen.findByRole('button', { name: /상승흐름/ }))

    const toggle = await screen.findByRole('switch')
    expect(toggle).toHaveAttribute('aria-checked', 'false')
  })

  it('활성 규칙 + 확정 신호가 있으면 확정 상태를 표시한다', async () => {
    server.use(
      http.get(`${BASE}/alerts/:ticker`, () => HttpResponse.json([
        { id: 7, ticker: '005930', alert_type: 'uptrend', direction: 'above', target_price: 0, is_active: 1 },
      ])),
      http.get(`${BASE}/alerts/signals/:ticker`, () => HttpResponse.json([
        {
          id: 1, ticker: '005930', status: 'confirmed',
          confirmed_date: '2026-07-01', confirm_path: 'hold', breakout_date: '2026-06-25',
        },
      ])),
    )
    renderWithProviders(<PriceTargetPanel ticker="005930" currentPrice={70000} />)

    fireEvent.click(await screen.findByRole('button', { name: /상승흐름/ }))

    expect(await screen.findByText('상승흐름 확정')).toBeInTheDocument()
    expect(await screen.findByText(/07\/01/)).toBeInTheDocument()
  })

  it('토글을 켜면 uptrend 규칙 생성이 요청된다', async () => {
    let posted = null
    let scanned = null
    server.use(
      http.get(`${BASE}/alerts/:ticker`, () => HttpResponse.json([])),
      http.get(`${BASE}/alerts/signals/:ticker`, () => HttpResponse.json([])),
      http.post(`${BASE}/alerts/`, async ({ request }) => {
        posted = await request.json()
        return HttpResponse.json({ id: 9, ...posted, is_active: 1 })
      }),
      http.post(`${BASE}/alerts/signals/:ticker/scan`, ({ params }) => {
        scanned = params.ticker
        return HttpResponse.json({ scanned: true })
      }),
    )
    renderWithProviders(<PriceTargetPanel ticker="005930" currentPrice={70000} />)

    fireEvent.click(await screen.findByRole('button', { name: /상승흐름/ }))
    fireEvent.click(await screen.findByRole('switch'))

    await waitFor(() =>
      expect(posted).toMatchObject({ alert_type: 'uptrend', ticker: '005930' }))
    // 켜기 직후 즉시 스캔(B)이 해당 종목으로 호출됨
    await waitFor(() => expect(scanned).toBe('005930'))
  })
})
