import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  // 환경 변수는 프로젝트 루트의 .env 파일 사용
  envDir: '..',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
    extensions: ['.js', '.jsx', '.json', '.ts', '.tsx'],
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        ws: true,
      },
    },
  },
  build: {
    // 번들 크기 최적화
    rollupOptions: {
      output: {
        manualChunks: {
          // React 라이브러리 분리
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          // 데이터 페칭 라이브러리 분리
          'query-vendor': ['@tanstack/react-query'],
          // 차트 라이브러리 분리
          'chart-vendor': ['recharts'],
        },
      },
    },
    // 청크 크기 경고 임계값 (KB)
    chunkSizeWarningLimit: 600,
    // 소스맵 생성 (프로덕션에서는 false)
    sourcemap: false,
    // 압축 최적화 (esbuild가 terser보다 빠름)
    minify: 'esbuild',
  },
  // 레거시 브라우저 지원
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom', '@tanstack/react-query'],
  },
})
