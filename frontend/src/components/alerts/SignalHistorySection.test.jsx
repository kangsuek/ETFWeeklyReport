import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { renderWithProviders, screen, waitFor, fireEvent } from '../../test/utils'
import { server } from '../../test/mocks/server'
import SignalHistorySection from './SignalHistorySection'

const BASE = '*/api'

describe('SignalHistorySection', () => {
  it('down 방향 이력을 표시하고 비어있으면 안내한다', async () => {
    server.use(
      http.get(`${BASE}/alerts/downtrend`, () => HttpResponse.json({ items: [], unread_count: 0 })),
    )
    renderWithProviders(<SignalHistorySection direction="down" />)
    expect(await screen.findByText('확정된 하락흐름 신호가 없습니다')).toBeInTheDocument()
  })

  it('목록·미읽음 배지를 표시한다', async () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend`, () => HttpResponse.json({
        items: [
          { id: 1, ticker: '005930', message: '[삼성전자] 상승흐름 확정', triggered_at: '2026-07-01' },
        ],
        unread_count: 1,
      })),
    )
    renderWithProviders(<SignalHistorySection direction="up" />)
    expect(await screen.findByText(/삼성전자.*상승흐름 확정/)).toBeInTheDocument()
    expect(screen.getByText('읽음 표시')).toBeInTheDocument()
  })

  it('삭제 버튼을 누르면 해당 이력이 제거된다', async () => {
    let items = [{ id: 1, ticker: '005930', message: '[삼성전자] 하락흐름 확정', triggered_at: '2026-07-01' }]
    let deletedId = null
    server.use(
      http.get(`${BASE}/alerts/downtrend`, () =>
        HttpResponse.json({ items, unread_count: items.length })),
      http.delete(`${BASE}/alerts/downtrend/:id`, ({ params }) => {
        deletedId = Number(params.id)
        items = items.filter(i => i.id !== deletedId)
        return HttpResponse.json({ deleted: true })
      }),
    )
    renderWithProviders(<SignalHistorySection direction="down" />)

    fireEvent.click(await screen.findByLabelText('삭제'))

    await waitFor(() => expect(deletedId).toBe(1))
    await waitFor(() =>
      expect(screen.getByText('확정된 하락흐름 신호가 없습니다')).toBeInTheDocument())
  })
})
