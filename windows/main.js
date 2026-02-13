const { app, BrowserWindow, protocol, net, ipcMain, dialog } = require('electron');
const { spawn, execSync } = require('child_process');
const path = require('path');
const http = require('http');
const fs = require('fs');
const crypto = require('crypto');
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
const BACKEND_PORT = 18000;
const HEALTH_CHECK_URL = `http://localhost:${BACKEND_PORT}/api/health`;
const HEALTH_CHECK_INTERVAL_MS = 500;
const HEALTH_CHECK_TIMEOUT_MS = 60000;

// ─── State ───────────────────────────────────────────────────────────────
let mainWindow = null;
let loadingWindow = null;
let backendProcess = null;

// ─── Path Helpers ────────────────────────────────────────────────────────
function isPackaged() {
  return app.isPackaged;
}

/** 번들된 백엔드 소스코드 경로 (읽기 전용) */
function getBundledBackendPath() {
  if (isPackaged()) {
    return path.join(process.resourcesPath, 'backend');
  }
  return path.join(__dirname, '..', 'backend');
}

/** 번들된 프론트엔드 dist 경로 (읽기 전용) */
function getFrontendDistPath() {
  if (isPackaged()) {
    return path.join(process.resourcesPath, 'frontend-dist');
  }
  return path.join(__dirname, '..', 'frontend', 'dist');
}

/**
 * 쓰기 가능한 작업 디렉토리 (패키징 모드)
 * Windows: %APPDATA%\ETF Weekly Report\
 */
function getWorkspacePath() {
  return app.getPath('userData');
}

// ─── Logging ─────────────────────────────────────────────────────────────
function getLogPath() {
  const logDir = path.join(getWorkspacePath(), 'logs');
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
  return logDir;
}

let logStream = null;

function initLogger() {
  const logFile = path.join(getLogPath(), 'app.log');
  logStream = fs.createWriteStream(logFile, { flags: 'a' });
}

function log(level, message) {
  const timestamp = new Date().toISOString();
  const line = `[${timestamp}] [${level}] ${message}`;
  console.log(line);
  if (logStream) {
    logStream.write(line + '\n');
  }
}

// ─── Loading Window ──────────────────────────────────────────────────────
function createLoadingWindow() {
  loadingWindow = new BrowserWindow({
    width: 400,
    height: 320,
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
  log('INFO', `Loading status: ${message}`);
  if (loadingWindow && !loadingWindow.isDestroyed()) {
    loadingWindow.webContents.send('backend-status', message);
  }
}

// ─── Main Window ─────────────────────────────────────────────────────────
function createMainWindow() {
  const iconPath = path.join(__dirname, 'icons', 'icon.png');
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    show: false,
    icon: fs.existsSync(iconPath) ? iconPath : undefined,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

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
    const url = new URL(request.url);
    let urlPath = decodeURIComponent(url.pathname);

    // /api 요청은 백엔드 서버로 프록시
    if (urlPath.startsWith('/api')) {
      const backendUrl = `http://localhost:${BACKEND_PORT}${urlPath}${url.search || ''}`;
      const fetchOptions = {
        method: request.method,
        headers: request.headers,
      };
      if (request.method !== 'GET' && request.method !== 'HEAD' && request.body) {
        fetchOptions.body = request.body;
        fetchOptions.duplex = 'half';
      }
      return net.fetch(backendUrl, fetchOptions);
    }

    // 정적 파일 서빙
    const frontendDist = getFrontendDistPath();

    if (urlPath === '/' || urlPath === './') {
      urlPath = '/index.html';
    }

    const filePath = path.join(frontendDist, urlPath);

    if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
      return net.fetch(`file://${filePath}`);
    }

    return net.fetch(`file://${path.join(frontendDist, 'index.html')}`);
  });
}

// ─── uv 경로 탐색 (Windows) ─────────────────────────────────────────────
function findUvPath() {
  const home = process.env.USERPROFILE || process.env.HOME || '';

  const commonPaths = [
    path.join(home, '.local', 'bin', 'uv.exe'),
    path.join(home, '.cargo', 'bin', 'uv.exe'),
    'C:\\Program Files\\uv\\uv.exe',
    'C:\\Program Files (x86)\\uv\\uv.exe',
    path.join(home, 'AppData', 'Local', 'uv', 'uv.exe'),
    path.join(home, '.uv', 'bin', 'uv.exe'),
  ];

  for (const p of commonPaths) {
    if (fs.existsSync(p)) {
      log('INFO', `Found uv at: ${p}`);
      return p;
    }
  }

  // 마지막 시도: where (Windows의 which)
  try {
    const uvPath = execSync('where uv', { encoding: 'utf-8' }).trim().split('\n')[0].trim();
    if (uvPath && fs.existsSync(uvPath)) {
      log('INFO', `Found uv via where: ${uvPath}`);
      return uvPath;
    }
  } catch {
    // where failed
  }

  return null;
}

// ─── uv 자동 설치 (Windows) ──────────────────────────────────────────────
async function installUv() {
  sendLoadingStatus('uv 설치 중...');
  log('INFO', 'Installing uv via PowerShell...');

  try {
    execSync(
      'powershell -NonInteractive -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"',
      {
        encoding: 'utf-8',
        timeout: 120000,
        env: { ...process.env },
      }
    );
    log('INFO', 'uv installation command completed');
  } catch (err) {
    log('ERROR', `uv installation failed: ${err.message}`);
    if (err.stderr) log('ERROR', `stderr: ${err.stderr.slice(0, 1000)}`);
    return null;
  }

  // 설치 후 재탐색
  const uvPath = findUvPath();
  if (uvPath) {
    log('INFO', `uv installed successfully at: ${uvPath}`);
  } else {
    log('ERROR', 'uv installation seemed to succeed but binary not found');
  }
  return uvPath;
}

// ─── .env 파일 파서 ─────────────────────────────────────────────────────
function parseEnvFile(envPath) {
  const vars = {};
  if (!fs.existsSync(envPath)) return vars;

  const content = fs.readFileSync(envPath, 'utf-8');
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    const eqIndex = trimmed.indexOf('=');
    if (eqIndex === -1) continue;

    const key = trimmed.substring(0, eqIndex).trim();
    let value = trimmed.substring(eqIndex + 1).trim();

    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }

    if (value.startsWith('your_')) continue;

    vars[key] = value;
  }
  return vars;
}

function loadUserEnv(env) {
  const workspace = getWorkspacePath();
  const userEnvPath = path.join(workspace, '.env');
  const userVars = parseEnvFile(userEnvPath);

  let count = 0;
  for (const [key, value] of Object.entries(userVars)) {
    if (!env[key]) {
      env[key] = value;
      count++;
    }
  }

  log('INFO', `Loaded ${count} env vars from ${userEnvPath}`);

  if (env.NAVER_CLIENT_ID && env.NAVER_CLIENT_ID !== 'your_naver_client_id') {
    log('INFO', 'Naver API credentials found');
  } else {
    log('WARN', `Naver API credentials not configured. Edit: ${userEnvPath}`);
  }
}

// ─── 백엔드 환경 설정 (패키징 모드) ─────────────────────────────────────
function fileHash(filePath) {
  const content = fs.readFileSync(filePath);
  return crypto.createHash('md5').update(content).digest('hex');
}

async function setupBackendWorkspace(uvPath) {
  if (!isPackaged()) return true;

  const workspace = getWorkspacePath();
  const bundledBackend = getBundledBackendPath();
  const venvPath = path.join(workspace, '.venv');
  const dataDir = path.join(workspace, 'data');
  const configDir = path.join(workspace, 'config');
  const hashFile = path.join(workspace, '.requirements-hash');

  for (const dir of [dataDir, configDir]) {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }

  // stocks.json 복사 (없을 때만)
  const bundledStocks = path.join(bundledBackend, 'config', 'stocks.json');
  const userStocks = path.join(configDir, 'stocks.json');
  if (!fs.existsSync(userStocks) && fs.existsSync(bundledStocks)) {
    fs.copyFileSync(bundledStocks, userStocks);
    log('INFO', 'Copied stocks.json to user config directory');
  }

  // .env 복사 (없을 때만)
  const userEnv = path.join(workspace, '.env');
  if (!fs.existsSync(userEnv)) {
    const bundledEnvExample = path.join(process.resourcesPath, '.env.example');
    if (fs.existsSync(bundledEnvExample)) {
      fs.copyFileSync(bundledEnvExample, userEnv);
      log('INFO', 'Copied .env.example to user .env');
    }
  }

  // requirements.txt 해시 비교 → 변경 시 재설치
  const reqPath = path.join(bundledBackend, 'requirements.txt');
  const currentHash = fs.existsSync(reqPath) ? fileHash(reqPath) : '';
  const savedHash = fs.existsSync(hashFile) ? fs.readFileSync(hashFile, 'utf-8').trim() : '';
  const needsInstall = !fs.existsSync(venvPath) || currentHash !== savedHash;

  if (!needsInstall) {
    log('INFO', 'Backend workspace is up to date');
    return true;
  }

  // venv 생성
  if (!fs.existsSync(venvPath)) {
    sendLoadingStatus('Python 가상환경 생성 중...');
    log('INFO', 'Creating Python virtual environment...');
    try {
      execSync(`"${uvPath}" venv "${venvPath}"`, {
        cwd: bundledBackend,
        encoding: 'utf-8',
        timeout: 30000,
      });
      log('INFO', 'Virtual environment created');
    } catch (err) {
      log('ERROR', `Failed to create venv: ${err.message}`);
      dialog.showErrorBox(
        'Python 환경 생성 실패',
        `가상환경을 만들 수 없습니다.\n\nPython 3.11 이상이 설치되어 있는지 확인해주세요.\n\n${err.message}`
      );
      return false;
    }
  }

  // 패키지 설치 (Windows: Scripts\python.exe)
  sendLoadingStatus('Python 패키지 설치 중... (첫 실행 시 1~2분 소요)');
  log('INFO', 'Installing Python packages...');
  try {
    const pythonExe = path.join(venvPath, 'Scripts', 'python.exe');
    const result = execSync(
      `"${uvPath}" pip install -r "${reqPath}" --python "${pythonExe}"`,
      {
        cwd: bundledBackend,
        encoding: 'utf-8',
        timeout: 300000,
        env: {
          ...process.env,
          PATH: `${path.dirname(uvPath)};${process.env.PATH || ''}`,
          VIRTUAL_ENV: venvPath,
        },
      }
    );
    log('INFO', `Package installation output: ${result.slice(0, 500)}`);
  } catch (err) {
    log('ERROR', `Failed to install packages: ${err.message}`);
    if (err.stderr) log('ERROR', `stderr: ${err.stderr.slice(0, 1000)}`);
    dialog.showErrorBox(
      '패키지 설치 실패',
      `Python 패키지를 설치할 수 없습니다.\n\n인터넷 연결을 확인해주세요.\n\n${err.message}`
    );
    return false;
  }

  fs.writeFileSync(hashFile, currentHash, 'utf-8');
  log('INFO', 'Backend workspace setup complete');
  return true;
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
  const portInUse = await isPortInUse(BACKEND_PORT);
  if (portInUse) {
    log('ERROR', `Port ${BACKEND_PORT} is already in use by another process`);
    dialog.showErrorBox(
      '포트 충돌',
      `포트 ${BACKEND_PORT}이 이미 다른 프로세스에서 사용 중입니다.\n\n` +
      `다른 ETF Weekly Report 인스턴스가 실행 중인지 확인해주세요.\n` +
      `앱을 종료한 후 다시 시도해주세요.`
    );
    return false;
  }

  let uvPath = findUvPath();
  if (!uvPath) {
    log('INFO', 'uv not found, attempting automatic installation...');
    uvPath = await installUv();
    if (!uvPath) {
      dialog.showErrorBox(
        'uv 설치 실패',
        'Python 패키지 매니저 uv를 자동으로 설치할 수 없었습니다.\n\n' +
        '수동으로 설치해주세요:\n' +
        'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"\n\n' +
        '설치 후 앱을 다시 시작해주세요.'
      );
      return false;
    }
  }

  if (isPackaged()) {
    const setupOk = await setupBackendWorkspace(uvPath);
    if (!setupOk) return false;
  }

  sendLoadingStatus('백엔드 서버를 시작하는 중...');

  const backendPath = getBundledBackendPath();
  const env = {
    ...process.env,
    PATH: `${path.dirname(uvPath)};${process.env.PATH || ''}`,
    CORS_ORIGINS: 'http://localhost:5173,http://localhost:3000,app://localhost',
  };

  let pythonCmd;
  let args;

  if (isPackaged()) {
    const workspace = getWorkspacePath();
    const venvPython = path.join(workspace, '.venv', 'Scripts', 'python.exe');
    const dataDir = path.join(workspace, 'data');
    const configDir = path.join(workspace, 'config');

    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }

    pythonCmd = venvPython;
    args = ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT), '--no-access-log'];

    env.DATABASE_URL = `sqlite:///${path.join(dataDir, 'etf_data.db')}`;
    env.STOCK_CONFIG_PATH = path.join(configDir, 'stocks.json');
    env.VIRTUAL_ENV = path.join(workspace, '.venv');
    env.LOG_LEVEL = 'INFO';

    loadUserEnv(env);

    const apiKeysPath = path.join(configDir, 'api-keys.json');
    if (fs.existsSync(apiKeysPath)) {
      try {
        const apiKeys = JSON.parse(fs.readFileSync(apiKeysPath, 'utf-8'));
        for (const [key, value] of Object.entries(apiKeys)) {
          if (value && !value.startsWith('your_')) {
            env[key] = value;
          }
        }
        log('INFO', `Loaded API keys from ${apiKeysPath}`);
      } catch (err) {
        log('WARN', `Failed to parse api-keys.json: ${err.message}`);
      }
    }

    log('INFO', `Starting backend: ${pythonCmd} ${args.join(' ')}`);
    log('INFO', `CWD: ${backendPath}`);
    log('INFO', `DATABASE_URL: ${env.DATABASE_URL}`);
    log('INFO', `STOCK_CONFIG_PATH: ${env.STOCK_CONFIG_PATH}`);
  } else {
    pythonCmd = uvPath;
    args = ['run', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT), '--no-access-log'];
    log('INFO', `Starting backend (dev): ${pythonCmd} ${args.join(' ')}`);
  }

  backendProcess = spawn(pythonCmd, args, {
    cwd: backendPath,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  backendProcess.stdout.on('data', (data) => {
    log('BACKEND', data.toString().trim());
  });

  backendProcess.stderr.on('data', (data) => {
    log('BACKEND-ERR', data.toString().trim());
  });

  backendProcess.on('error', (err) => {
    log('ERROR', `Failed to start backend: ${err.message}`);
    dialog.showErrorBox(
      '백엔드 시작 실패',
      `서버를 시작할 수 없습니다: ${err.message}`
    );
  });

  backendProcess.on('exit', (code, signal) => {
    log('INFO', `Backend exited with code=${code}, signal=${signal}`);
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
    if (!backendProcess) {
      log('ERROR', 'Backend process exited before becoming ready');
      dialog.showErrorBox(
        '백엔드 시작 실패',
        '백엔드 서버가 시작 중 종료되었습니다.\n\n' +
        `상세 로그: ${path.join(getLogPath(), 'app.log')}`
      );
      return false;
    }

    const healthy = await checkHealth();
    if (healthy) {
      sendLoadingStatus('앱을 로드하는 중...');
      log('INFO', `Backend ready after ${Date.now() - startTime}ms`);
      return true;
    }
    await new Promise((r) => setTimeout(r, HEALTH_CHECK_INTERVAL_MS));
  }

  const logPath = path.join(getLogPath(), 'app.log');
  dialog.showErrorBox(
    '서버 시작 시간 초과',
    '백엔드 서버가 시작되지 않았습니다.\n\n' +
    'Python 3.11+ 및 uv가 설치되어 있는지 확인해주세요.\n\n' +
    `상세 로그: ${logPath}`
  );
  return false;
}

// ─── Process Termination (Windows) ───────────────────────────────────────
function stopBackend() {
  if (backendProcess) {
    log('INFO', 'Stopping backend process...');
    const pid = backendProcess.pid;

    // Windows: use taskkill to terminate the process tree
    try {
      execSync(`taskkill /PID ${pid} /T /F`, { encoding: 'utf-8', timeout: 5000 });
      log('INFO', 'Backend process terminated via taskkill');
    } catch {
      // taskkill may fail if process already exited; try regular kill as fallback
      try {
        backendProcess.kill();
      } catch {
        // already dead
      }
    }

    backendProcess = null;
  }
}

// ─── IPC Handlers ────────────────────────────────────────────────────────
function setupIpcHandlers() {
  ipcMain.handle('get-app-version', () => app.getVersion());
}

// ─── App Lifecycle ───────────────────────────────────────────────────────
app.whenReady().then(async () => {
  initLogger();
  log('INFO', `App starting (packaged=${isPackaged()})`);
  log('INFO', `Platform: ${process.platform} ${process.arch}`);
  log('INFO', `Electron: ${process.versions.electron}`);
  log('INFO', `userData: ${getWorkspacePath()}`);

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
