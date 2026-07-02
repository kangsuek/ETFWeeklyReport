/* ESLint 설정 (ESLint 8, eslintrc 형식) — Vite + React 18 */
module.exports = {
  root: true,
  env: { browser: true, es2021: true, node: true },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: [
    'dist',
    'coverage',
    'node_modules',
    '.eslintrc.cjs',
    'public',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
  },
  settings: { react: { version: '18.2' } },
  plugins: ['react-refresh'],
  // 레거시 코드에 eslint를 도입하는 baseline.
  // 기존 대량 위반 규칙은 경고로 두고 점진적으로 error로 승격한다.
  rules: {
    'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
    // PropTypes: 코드베이스 전반 미비(약 200건). CLAUDE.md 원칙상 목표는 error이나
    // 점진 도입을 위해 우선 off. 컴포넌트별 PropTypes 정비 후 'warn'→'error'로 승격 권장.
    'react/prop-types': 'off',
    // 기존 위반이 있어 baseline은 경고. (rules-of-hooks: 데이터 없을 때 early return 뒤
    // useMemo 호출 6건 등 실제 수정 필요) 점진 수정 후 error로 승격 권장.
    'react-hooks/rules-of-hooks': 'warn',
    'react-hooks/exhaustive-deps': 'warn',
    'no-case-declarations': 'warn',
    'no-inner-declarations': 'warn',
  },
  overrides: [
    {
      // 테스트 파일: 테스트 전역(vitest) 허용
      files: ['**/*.test.{js,jsx}', '**/tests/**', '**/__tests__/**', 'src/test/**'],
      env: { node: true },
      globals: {
        describe: 'readonly',
        it: 'readonly',
        test: 'readonly',
        expect: 'readonly',
        beforeEach: 'readonly',
        afterEach: 'readonly',
        beforeAll: 'readonly',
        afterAll: 'readonly',
        vi: 'readonly',
      },
    },
  ],
}
