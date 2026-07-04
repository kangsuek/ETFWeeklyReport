import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import { alertApi } from '../services/api'

// 신호는 16:40 스캔·앱 시작 시에만 생기므로 저빈도(10분) 폴링으로 충분.
// 앱 실행 중 상시 폴링(장중 한정 아님) — 장 마감 후·기동 시 신호를 당일 반영.
const POLL_INTERVAL_MS = 10 * 60 * 1000

/**
 * 상승흐름(uptrend) 확정 알림 이력·미읽음 폴링 훅.
 *
 * 기존 AlertContext(벨/토스트, 3종 상태 알림)와 완전히 분리된 서버 이력 기반이다.
 *
 * @returns {{ items: Array, unreadCount: number, isLoading: boolean, markRead: Function }}
 */
export function useUptrendAlerts() {
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['uptrendAlerts'],
    queryFn: async () => {
      const res = await alertApi.getUptrend()
      return res.data
    },
    refetchInterval: POLL_INTERVAL_MS,
    refetchIntervalInBackground: true,
    staleTime: POLL_INTERVAL_MS,
  })

  const markRead = useCallback(async () => {
    await alertApi.markUptrendRead()
    await queryClient.invalidateQueries({ queryKey: ['uptrendAlerts'] })
  }, [queryClient])

  return {
    items: data?.items ?? [],
    unreadCount: data?.unread_count ?? 0,
    isLoading,
    markRead,
  }
}

export default useUptrendAlerts
