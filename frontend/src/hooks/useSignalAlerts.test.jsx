import { describe, it, expect } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '../test/mocks/server'
import { useSignalAlerts } from './useSignalAlerts'

const BASE = '*/api'

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

describe('useSignalAlerts', () => {
  it('uptrend unread_count를 노출한다', async () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend`, () =>
        HttpResponse.json({ items: [{ id: 1 }], unread_count: 2 })),
    )
    const { result } = renderHook(() => useSignalAlerts('uptrend'), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.unreadCount).toBe(2))
  })

  it('downtrend는 downtrend 엔드포인트를 조회한다', async () => {
    server.use(
      http.get(`${BASE}/alerts/downtrend`, () =>
        HttpResponse.json({ items: [{ id: 9 }], unread_count: 5 })),
    )
    const { result } = renderHook(() => useSignalAlerts('downtrend'), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.unreadCount).toBe(5))
  })

  it('markRead 후 미읽음이 0이 된다', async () => {
    let unread = 3
    server.use(
      http.get(`${BASE}/alerts/downtrend`, () =>
        HttpResponse.json({ items: [], unread_count: unread })),
      http.post(`${BASE}/alerts/downtrend/read`, () => {
        unread = 0
        return HttpResponse.json({ read: true })
      }),
    )
    const { result } = renderHook(() => useSignalAlerts('downtrend'), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.unreadCount).toBe(3))

    await act(async () => { await result.current.markRead() })

    await waitFor(() => expect(result.current.unreadCount).toBe(0))
  })
})
