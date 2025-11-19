import { Suspense, lazy } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SettingsProvider } from './contexts/SettingsContext'
import { ToastProvider } from './contexts/ToastContext'
import ErrorBoundary from './components/common/ErrorBoundary'
import ToastContainer from './components/common/ToastContainer'
import Header from './components/layout/Header'
import Footer from './components/layout/Footer'
import LoadingIndicator from './components/common/LoadingIndicator'

// Lazy loading pages
const Dashboard = lazy(() => import('./pages/Dashboard'))
const ETFDetail = lazy(() => import('./pages/ETFDetail'))
const Comparison = lazy(() => import('./pages/Comparison'))
const Settings = lazy(() => import('./pages/Settings'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30 * 1000, // 30 seconds (실시간 데이터 최적화)
    },
  },
})

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <SettingsProvider>
          <ToastProvider>
            <Router>
              <ErrorBoundary>
                <div className="flex flex-col min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
                  <Header />
                  <main className="flex-grow container mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
                    <ErrorBoundary>
                      <Suspense fallback={
                        <div className="flex justify-center items-center h-64">
                          <LoadingIndicator size="lg" text="페이지 로딩 중..." />
                        </div>
                      }>
                        <Routes>
                          <Route path="/" element={<Dashboard />} />
                          <Route path="/etf/:ticker" element={<ETFDetail />} />
                          <Route path="/compare" element={<Comparison />} />
                          <Route path="/settings" element={<Settings />} />
                        </Routes>
                      </Suspense>
                    </ErrorBoundary>
                  </main>
                  <Footer />
                </div>
              </ErrorBoundary>
              <ToastContainer />
            </Router>
          </ToastProvider>
        </SettingsProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
