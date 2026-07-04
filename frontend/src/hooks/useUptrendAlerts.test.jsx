import { describe, it, expect } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'
import { server } from '../test/mocks/server'
import { useUptrendAlerts } from './useUptrendAlerts'

const BASE = '*/api'

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

describe('useUptrendAlerts', () => {
  it('서버의 unread_count를 노출한다', async () => {
    server.use(
      http.get(`${BASE}/alerts/uptrend`, () =>
        HttpResponse.json({ items: [{ id: 1 }], unread_count: 2 })),
    )
    const { result } = renderHook(() => useUptrendAlerts(), { wrapper: makeWrapper() })

    await waitFor(() => expect(result.current.unreadCount).toBe(2))
    expect(result.current.items).toHaveLength(1)
  })

  it('markRead 호출 후 미읽음이 0이 된다', async () => {
    let unread = 2
    server.use(
      http.get(`${BASE}/alerts/uptrend`, () =>
        HttpResponse.json({ items: [], unread_count: unread })),
      http.post(`${BASE}/alerts/uptrend/read`, () => {
        unread = 0
        return HttpResponse.json({ read: true })
      }),
    )
    const { result } = renderHook(() => useUptrendAlerts(), { wrapper: makeWrapper() })
    await waitFor(() => expect(result.current.unreadCount).toBe(2))

    await act(async () => { await result.current.markRead() })

    await waitFor(() => expect(result.current.unreadCount).toBe(0))
  })
})
