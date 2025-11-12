import { describe, it, expect, vi } from 'vitest'
import { renderWithProviders, screen, waitFor } from '../../test/utils'
import TickerManagementPanel from './TickerManagementPanel'

// alert 모킹
global.alert = vi.fn()

describe('TickerManagementPanel 컴포넌트', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('컴포넌트가 정상적으로 렌더링된다', () => {
    renderWithProviders(<TickerManagementPanel />)

    // 초기 로딩 중에도 존재하는 요소들 확인
    expect(document.querySelector('.bg-white')).toBeInTheDocument()
  })

  it('로딩 상태가 정상적으로 표시된다', () => {
    renderWithProviders(<TickerManagementPanel />)

    // 로딩 스켈레톤 확인
    const skeleton = document.querySelector('.animate-pulse')
    expect(skeleton).toBeInTheDocument()
  })
})
