import { useState } from 'react'
import PageHeader from '../components/common/PageHeader'
import TickerManagementPanel from '../components/settings/TickerManagementPanel'

export default function Settings() {
  return (
    <div className="max-w-7xl mx-auto px-2 sm:px-0">
      <PageHeader
        title="설정"
        description="종목 관리 및 환경 설정"
      />

      {/* 종목 관리 섹션 */}
      <div className="mt-4 sm:mt-6">
        <TickerManagementPanel />
      </div>
    </div>
  )
}
