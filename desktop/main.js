const { app, BrowserWindow, protocol, net, ipcMain, dialog } = require('electron');
const { spawn, execSync } = require('child_process');
const path = require('path');
const http = require('http');
const fs = require('fs');
const nodenet = require('net');

// ─── Scheme Registration (must be before app.ready) ──────────────────────
protocol.registerSchemesAsPrivileged([
  {
    scheme: 'app',
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      corsEnabled: true,
    },
  },
]);

// ─── Constants ───────────────────────────────────────────────────────────
const BACKEND_PORT = 8000;
const HEALTH_CHECK_URL = `http://localhost:${BACKEND_PORT}/api/health`;
const HEALTH_CHECK_INTERVAL_MS = 500;
const HEALTH_CHECK_TIMEOUT_MS = 30000;

// ─── Paths ───────────────────────────────────────────────────────────────
function isPackaged() {
  return app.isPackaged;
}

function getBackendPath() {
  if (isPackaged()) {
    return path.join(process.resourcesPath, 'backend');
  }
  return path.join(__dirname, '..', 'backend');
}

function getFrontendDistPath() {
  if (isPackaged()) {
    return path.join(process.resourcesPath, 'frontend-dist');
  }
  return path.join(__dirname, '..', 'frontend', 'dist');
}

function getDataPath() {
  // 패키징된 앱에서는 Application Support에 데이터 저장
  if (isPackaged()) {
    const dataDir = path.join(app.getPath('userData'), 'data');
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }
    return dataDir;
  }
  return null; // 개발 모드에서는 기본 경로 사용
}

// ─── State ───────────────────────────────────────────────────────────────
let mainWindow = null;
let loadingWindow = null;
let backendProcess = null;

// ─── Loading Window ──────────────────────────────────────────────────────
function createLoadingWindow() {
  loadingWindow = new BrowserWindow({
    width: 400,
    height: 300,
    frame: false,
    transparent: false,
    resizable: false,
    center: true,
    show: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  loadingWindow.loadFile(path.join(__dirname, 'loading.html'));
}

function sendLoadingStatus(message) {
  if (loadingWindow && !loadingWindow.isDestroyed()) {
    loadingWindow.webContents.send('backend-status', message);
  }
}

// ─── Main Window ─────────────────────────────────────────────────────────
function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // app:// 프로토콜로 프론트엔드 로드 (origin: app://localhost)
  // 경로를 '/'로 설정해야 React Router의 path="/"와 매칭됨
  mainWindow.loadURL('app://localhost/');

  mainWindow.once('ready-to-show', () => {
    if (loadingWindow && !loadingWindow.isDestroyed()) {
      loadingWindow.close();
      loadingWindow = null;
    }
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ─── Custom Protocol (app://) ────────────────────────────────────────────
function registerAppProtocol() {
  protocol.handle('app', (request) => {
    const frontendDist = getFrontendDistPath();
    let urlPath = decodeURIComponent(new URL(request.url).pathname);

    // 루트 요청 → index.html
    if (urlPath === '/' || urlPath === './') {
      urlPath = '/index.html';
    }

    const filePath = path.join(frontendDist, urlPath);

    // 파일이 존재하면 그대로 서빙, 아니면 index.html (SPA fallback)
    if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
      return net.fetch(`file://${filePath}`);
    }

    // SPA fallback: index.html 반환 (BrowserRouter 지원)
    return net.fetch(`file://${path.join(frontendDist, 'index.html')}`);
  });
}

// ─── Python/uv Check ─────────────────────────────────────────────────────
function findUvPath() {
  try {
    const uvPath = execSync('which uv', { encoding: 'utf-8' }).trim();
    if (uvPath) return uvPath;
  } catch {
    // which failed
  }

  // 일반적인 설치 경로 시도
  const commonPaths = [
    path.join(process.env.HOME, '.local', 'bin', 'uv'),
    path.join(process.env.HOME, '.cargo', 'bin', 'uv'),
    '/usr/local/bin/uv',
    '/opt/homebrew/bin/uv',
  ];

  for (const p of commonPaths) {
    if (fs.existsSync(p)) return p;
  }

  return null;
}

// ─── Backend Management ──────────────────────────────────────────────────
async function isPortInUse(port) {
  return new Promise((resolve) => {
    const server = nodenet.createServer();
    server.once('error', () => resolve(true));
    server.once('listening', () => {
      server.close();
      resolve(false);
    });
    server.listen(port);
  });
}

async function startBackend() {
  // 이미 실행 중인지 확인
  const portInUse = await isPortInUse(BACKEND_PORT);
  if (portInUse) {
    console.log(`Port ${BACKEND_PORT} already in use, checking if backend is running...`);
    const healthy = await checkHealth();
    if (healthy) {
      console.log('Backend is already running');
      return true;
    }
  }

  const uvPath = findUvPath();
  if (!uvPath) {
    dialog.showErrorBox(
      'uv를 찾을 수 없습니다',
      'Python 패키지 매니저 uv가 설치되어 있지 않습니다.\n\n' +
      '다음 명령으로 설치해주세요:\n' +
      'curl -LsSf https://astral.sh/uv/install.sh | sh\n\n' +
      '설치 후 앱을 다시 시작해주세요.'
    );
    return false;
  }

  sendLoadingStatus('백엔드 서버를 시작하는 중...');

  const backendPath = getBackendPath();
  const env = { ...process.env, PATH: `${path.dirname(uvPath)}:${process.env.PATH}` };

  // 패키징된 앱에서는 데이터 경로 설정
  const dataPath = getDataPath();
  if (dataPath) {
    env.DATABASE_PATH = path.join(dataPath, 'etf_data.db');
    env.STOCK_CONFIG_PATH = path.join(backendPath, 'config', 'stocks.json');
  }

  backendProcess = spawn(uvPath, ['run', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)], {
    cwd: backendPath,
    env,
    stdio: ['ignore', 'ignore', 'ignore'],
  });

  backendProcess.on('error', (err) => {
    console.error('Failed to start backend:', err);
    dialog.showErrorBox(
      '백엔드 시작 실패',
      `서버를 시작할 수 없습니다: ${err.message}`
    );
  });

  backendProcess.on('exit', (code, signal) => {
    console.log(`Backend exited with code ${code}, signal ${signal}`);
    backendProcess = null;
  });

  return true;
}

function checkHealth() {
  return new Promise((resolve) => {
    const req = http.get(HEALTH_CHECK_URL, { timeout: 2000 }, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForBackend() {
  sendLoadingStatus('백엔드 준비 대기 중...');

  const startTime = Date.now();
  while (Date.now() - startTime < HEALTH_CHECK_TIMEOUT_MS) {
    const healthy = await checkHealth();
    if (healthy) {
      sendLoadingStatus('앱을 로드하는 중...');
      return true;
    }
    await new Promise((r) => setTimeout(r, HEALTH_CHECK_INTERVAL_MS));
  }

  dialog.showErrorBox(
    '서버 시작 시간 초과',
    '백엔드 서버가 30초 내에 시작되지 않았습니다.\n\n' +
    'Python 3.11+ 및 필요한 패키지가 설치되어 있는지 확인해주세요.'
  );
  return false;
}

function stopBackend() {
  if (backendProcess) {
    console.log('Stopping backend process...');
    backendProcess.kill('SIGTERM');

    // 5초 후에도 종료되지 않으면 강제 종료
    setTimeout(() => {
      if (backendProcess) {
        console.log('Force killing backend process...');
        backendProcess.kill('SIGKILL');
        backendProcess = null;
      }
    }, 5000);
  }
}

// ─── IPC Handlers ────────────────────────────────────────────────────────
function setupIpcHandlers() {
  ipcMain.handle('get-app-version', () => app.getVersion());
}

// ─── App Lifecycle ───────────────────────────────────────────────────────
app.whenReady().then(async () => {
  registerAppProtocol();
  setupIpcHandlers();
  createLoadingWindow();

  const started = await startBackend();
  if (!started) {
    app.quit();
    return;
  }

  const ready = await waitForBackend();
  if (!ready) {
    stopBackend();
    app.quit();
    return;
  }

  createMainWindow();
});

app.on('window-all-closed', () => {
  stopBackend();
  app.quit();
});

app.on('before-quit', () => {
  stopBackend();
});

app.on('activate', () => {
  if (mainWindow === null && !loadingWindow) {
    createMainWindow();
  }
});
