import { describe, it, expect } from 'vitest'
import { http, HttpResponse } from 'msw'
import { renderWithProviders, screen, waitFor, fireEvent } from '../../test/utils'
import { server } from '../../test/mocks/server'
import UptrendHistorySection from './UptrendHistorySection'

const BASE = '*/api'

describe('UptrendHistorySection', () => {
  it('이력이 없으면 빈 상태를 표시한다', async () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend`, () =>
        HttpResponse.json({ items: [], unread_count: 0 })),
    )
    renderWithProviders(<UptrendHistorySection />)

    expect(await screen.findByText('확정된 상승흐름 신호가 없습니다')).toBeInTheDocument()
  })

  it('이력 목록과 미읽음 배지를 표시한다', async () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend`, () => HttpResponse.json({
        items: [
          { id: 1, ticker: '005930', message: '[삼성전자] 상승흐름 확정 — 돌파 후 3일 연속 유지', triggered_at: '2026-07-01' },
          { id: 2, ticker: '000660', message: '[SK하이닉스] 상승흐름 확정 — 재시험 성공', triggered_at: '2026-07-02' },
        ],
        unread_count: 2,
      })),
    )
    renderWithProviders(<UptrendHistorySection />)

    expect(await screen.findByText(/삼성전자.*상승흐름 확정/)).toBeInTheDocument()
    expect(screen.getByText(/SK하이닉스.*재시험 성공/)).toBeInTheDocument()
    expect(screen.getByText('읽음 표시')).toBeInTheDocument()
  })

  it('삭제 버튼을 누르면 해당 이력이 제거된다', async () => {
    let items = [
      { id: 1, ticker: '005930', message: '[삼성전자] 상승흐름 확정', triggered_at: '2026-07-01' },
    ]
    let deletedId = null
    server.use(
      http.get(`${BASE}/alerts/uptrend`, () =>
        HttpResponse.json({ items, unread_count: items.length })),
      http.delete(`${BASE}/alerts/uptrend/:id`, ({ params }) => {
        deletedId = Number(params.id)
        items = items.filter(i => i.id !== deletedId)
        return HttpResponse.json({ deleted: true })
      }),
    )
    renderWithProviders(<UptrendHistorySection />)

    fireEvent.click(await screen.findByLabelText('삭제'))

    await waitFor(() => expect(deletedId).toBe(1))
    await waitFor(() =>
      expect(screen.getByText('확정된 상승흐름 신호가 없습니다')).toBeInTheDocument())
  })
})
