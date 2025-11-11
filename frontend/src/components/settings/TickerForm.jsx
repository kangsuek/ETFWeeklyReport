import { useState, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { settingsApi } from '../../services/api'

export default function TickerForm({ mode, initialData, onSubmit, onClose, isSubmitting }) {
  const [formData, setFormData] = useState({
    ticker: '',
    name: '',
    type: 'ETF',
    theme: '',
    launch_date: '',
    expense_ratio: '',
    search_keyword: '',
    relevance_keywords: [],
  })

  const [keywordsInput, setKeywordsInput] = useState('')
  const [errors, setErrors] = useState({})

  // 초기 데이터 설정 (수정 모드)
  useEffect(() => {
    if (mode === 'edit' && initialData) {
      setFormData({
        ticker: initialData.ticker || '',
        name: initialData.name || '',
        type: initialData.type || 'ETF',
        theme: initialData.theme || '',
        launch_date: initialData.launch_date || '',
        expense_ratio: initialData.expense_ratio || '',
        search_keyword: initialData.search_keyword || '',
        relevance_keywords: initialData.relevance_keywords || [],
      })
      setKeywordsInput((initialData.relevance_keywords || []).join(', '))
    }
  }, [mode, initialData])

  // 네이버 금융 자동 입력 Mutation
  const validateMutation = useMutation({
    mutationFn: (ticker) => settingsApi.validateTicker(ticker),
    onSuccess: (response) => {
      const data = response.data
      setFormData({
        ...formData,
        name: data.name || '',
        type: data.type || 'ETF',
        theme: data.theme || '',
        launch_date: data.launch_date || '',
        expense_ratio: data.expense_ratio || '',
        search_keyword: data.search_keyword || '',
        relevance_keywords: data.relevance_keywords || [],
      })
      setKeywordsInput((data.relevance_keywords || []).join(', '))
      alert('종목 정보를 자동으로 입력했습니다. 확인 후 저장하세요.')
    },
    onError: (error) => {
      alert(`종목 정보를 가져올 수 없습니다: ${error.message}`)
    },
  })

  const handleAutoFill = () => {
    if (!formData.ticker) {
      alert('티커 코드를 먼저 입력하세요.')
      return
    }
    validateMutation.mutate(formData.ticker)
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    // 에러 클리어
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: null }))
    }
  }

  const handleKeywordsChange = (e) => {
    const value = e.target.value
    setKeywordsInput(value)
    // 쉼표로 분리하여 배열로 변환
    const keywords = value
      .split(',')
      .map(k => k.trim())
      .filter(k => k.length > 0)
    setFormData(prev => ({ ...prev, relevance_keywords: keywords }))
  }

  const validate = () => {
    const newErrors = {}

    if (!formData.ticker) newErrors.ticker = '티커 코드는 필수입니다.'
    if (!formData.name) newErrors.name = '종목명은 필수입니다.'
    if (!formData.type) newErrors.type = '타입은 필수입니다.'
    if (!formData.theme) newErrors.theme = '테마는 필수입니다.'

    // ETF인 경우 추가 필드 검증
    if (formData.type === 'ETF') {
      if (!formData.launch_date) newErrors.launch_date = 'ETF는 상장일이 필수입니다.'
      if (!formData.expense_ratio) newErrors.expense_ratio = 'ETF는 운용보수가 필수입니다.'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return

    // 제출 데이터 준비
    const submitData = { ...formData }

    // STOCK인 경우 ETF 전용 필드 null로 설정
    if (submitData.type === 'STOCK') {
      submitData.launch_date = null
      submitData.expense_ratio = null
    }

    onSubmit(submitData)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-2 sm:p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[95vh] sm:max-h-[90vh] overflow-y-auto">
        {/* 헤더 */}
        <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-gray-200 flex items-center justify-between sticky top-0 bg-white rounded-t-lg z-10">
          <h3 className="text-base sm:text-lg font-semibold text-gray-900">
            {mode === 'create' ? '새 종목 추가' : '종목 수정'}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors p-1"
            disabled={isSubmitting}
          >
            <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 폼 */}
        <form onSubmit={handleSubmit} className="px-4 sm:px-6 py-3 sm:py-4 space-y-3 sm:space-y-4">
          {/* 티커 코드 + 자동 입력 버튼 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              티커 코드 <span className="text-red-500">*</span>
            </label>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="text"
                name="ticker"
                value={formData.ticker}
                onChange={handleChange}
                disabled={mode === 'edit' || isSubmitting}
                className="flex-1 px-3 py-2 text-sm sm:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                placeholder="예: 005930, 487240"
              />
              {mode === 'create' && (
                <button
                  type="button"
                  onClick={handleAutoFill}
                  disabled={!formData.ticker || validateMutation.isPending || isSubmitting}
                  className="w-full sm:w-auto px-3 sm:px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors whitespace-nowrap flex items-center justify-center gap-2 text-sm sm:text-base"
                >
                  {validateMutation.isPending ? (
                    <>
                      <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      로딩 중...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                      </svg>
                      <span className="hidden sm:inline">네이버에서 자동 입력</span>
                      <span className="sm:hidden">자동 입력</span>
                    </>
                  )}
                </button>
              )}
            </div>
            {errors.ticker && <p className="text-red-500 text-xs sm:text-sm mt-1">{errors.ticker}</p>}
            {mode === 'create' && (
              <p className="text-xs sm:text-sm text-gray-500 mt-1">
                티커 코드를 입력하고 "자동 입력" 버튼을 클릭하면 종목 정보가 자동으로 채워집니다.
              </p>
            )}
          </div>

          {/* 종목명 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              종목명 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              disabled={isSubmitting}
              className="w-full px-3 py-2 text-sm sm:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100"
              placeholder="예: 삼성전자, KODEX 2차전지산업"
            />
            {errors.name && <p className="text-red-500 text-sm mt-1">{errors.name}</p>}
          </div>

          {/* 타입 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              타입 <span className="text-red-500">*</span>
            </label>
            <select
              name="type"
              value={formData.type}
              onChange={handleChange}
              disabled={isSubmitting}
              className="w-full px-3 py-2 text-sm sm:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100"
            >
              <option value="ETF">ETF</option>
              <option value="STOCK">STOCK</option>
            </select>
            {errors.type && <p className="text-red-500 text-sm mt-1">{errors.type}</p>}
          </div>

          {/* 테마 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              테마 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="theme"
              value={formData.theme}
              onChange={handleChange}
              disabled={isSubmitting}
              className="w-full px-3 py-2 text-sm sm:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100"
              placeholder="예: 2차전지, 반도체, AI"
            />
            {errors.theme && <p className="text-red-500 text-sm mt-1">{errors.theme}</p>}
          </div>

          {/* ETF 전용 필드 */}
          {formData.type === 'ETF' && (
            <>
              {/* 상장일 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  상장일 <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  name="launch_date"
                  value={formData.launch_date}
                  onChange={handleChange}
                  disabled={isSubmitting}
                  className="w-full px-3 py-2 text-sm sm:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100"
                />
                {errors.launch_date && <p className="text-red-500 text-sm mt-1">{errors.launch_date}</p>}
              </div>

              {/* 운용보수 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  운용보수 (%) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  name="expense_ratio"
                  value={formData.expense_ratio}
                  onChange={handleChange}
                  disabled={isSubmitting}
                  className="w-full px-3 py-2 text-sm sm:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100"
                  placeholder="예: 0.50"
                />
                {errors.expense_ratio && <p className="text-red-500 text-sm mt-1">{errors.expense_ratio}</p>}
              </div>
            </>
          )}

          {/* 뉴스 검색 키워드 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              뉴스 검색 키워드
            </label>
            <input
              type="text"
              name="search_keyword"
              value={formData.search_keyword}
              onChange={handleChange}
              disabled={isSubmitting}
              className="w-full px-3 py-2 text-sm sm:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100"
              placeholder="예: 삼성전자"
            />
            <p className="text-sm text-gray-500 mt-1">
              뉴스 수집 시 사용할 검색 키워드입니다.
            </p>
          </div>

          {/* 관련 키워드 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              관련 키워드
            </label>
            <input
              type="text"
              value={keywordsInput}
              onChange={handleKeywordsChange}
              disabled={isSubmitting}
              className="w-full px-3 py-2 text-sm sm:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100"
              placeholder="쉼표로 구분하여 입력 (예: 삼성전자, 반도체, 전자)"
            />
            <p className="text-sm text-gray-500 mt-1">
              뉴스 관련성 판단에 사용할 키워드들을 쉼표로 구분하여 입력하세요.
            </p>
          </div>

          {/* 버튼 */}
          <div className="flex gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  저장 중...
                </>
              ) : (
                mode === 'create' ? '추가' : '수정'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
