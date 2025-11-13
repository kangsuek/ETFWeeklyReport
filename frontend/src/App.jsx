import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SettingsProvider } from './contexts/SettingsContext'
import { ToastProvider } from './contexts/ToastContext'
import ErrorBoundary from './components/common/ErrorBoundary'
import ToastContainer from './components/common/ToastContainer'
import Header from './components/layout/Header'
import Footer from './components/layout/Footer'
import Dashboard from './pages/Dashboard'
import ETFDetail from './pages/ETFDetail'
import Comparison from './pages/Comparison'
import Settings from './pages/Settings'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
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
                      <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/etf/:ticker" element={<ETFDetail />} />
                        <Route path="/compare" element={<Comparison />} />
                        <Route path="/settings" element={<Settings />} />
                      </Routes>
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
