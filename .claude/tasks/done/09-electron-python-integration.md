# Task 09: Electron ↔ Python Backend Integration

## Objective
Manage the Python backend process lifecycle from Electron — start, monitor, restart, and communicate.

## Steps

### 1. Python process manager (`electron/src/main/services/backend-manager.ts`)

```typescript
import { spawn, ChildProcess } from 'child_process';
import path from 'path';

class BackendManager {
  private process: ChildProcess | null = null;
  private port: number = 8765;
  private isReady: boolean = false;

  /**
   * Start the Python backend as a child process.
   * Handles both development (python from PATH) and
   * production (bundled Python or system Python).
   */
  async start(): Promise<void> {
    const pythonPath = await this.findPython();
    const backendDir = this.getBackendDir();

    this.process = spawn(pythonPath, [
      '-m', 'opennode',
      '--port', String(this.port),
    ], {
      cwd: backendDir,
      env: {
        ...process.env,
        OPENNODE_PORT: String(this.port),
      },
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    // Monitor stdout for "ready" signal
    this.process.stdout?.on('data', (data) => {
      const output = data.toString();
      if (output.includes('Application startup complete')) {
        this.isReady = true;
        this.emit('ready');
      }
    });

    // Monitor stderr for errors
    this.process.stderr?.on('data', (data) => {
      console.error('[Backend]', data.toString());
    });

    // Handle process exit
    this.process.on('exit', (code) => {
      this.isReady = false;
      if (code !== 0) {
        this.emit('error', `Backend exited with code ${code}`);
        // Auto-restart logic
      }
    });

    // Wait for ready with timeout
    await this.waitForReady(30000); // 30s timeout for model loading
  }

  /**
   * Find Python executable.
   * Priority: bundled > venv > system
   */
  private async findPython(): Promise<string> {
    // 1. Check for bundled Python (production)
    // 2. Check for venv in backend directory
    // 3. Fall back to system python3
  }

  /**
   * Health check via HTTP.
   */
  async checkHealth(): Promise<boolean> {
    try {
      const res = await fetch(`http://127.0.0.1:${this.port}/health`);
      return res.ok;
    } catch {
      return false;
    }
  }

  async stop(): Promise<void> {
    if (this.process) {
      this.process.kill('SIGTERM');
      // Wait for graceful shutdown, then SIGKILL
      setTimeout(() => this.process?.kill('SIGKILL'), 5000);
    }
  }
}
```

### 2. Python environment detection

Check for required dependencies:
```typescript
async function checkPythonEnvironment(): Promise<EnvironmentStatus> {
  // Check python version (>=3.10)
  // Check if required packages are installed
  // Check GPU availability (nvidia-smi)
  // Check available disk space for models
  return {
    pythonVersion: '3.11.0',
    packagesInstalled: true,
    gpuAvailable: true,
    gpuName: 'NVIDIA RTX 4070',
    modelsDownloaded: true,
    diskSpace: '15GB free'
  };
}
```

### 3. First-run setup wizard
If Python environment is not ready:
1. Detect if Python 3.10+ is installed
2. Offer to create venv and install dependencies
3. Offer to download ASR models (show size: ~2.5GB)
4. Show progress bar during download
5. Verify everything works

### 4. Port management
```typescript
async function findAvailablePort(preferred: number = 8765): Promise<number> {
  // Try preferred port first
  // If busy, try next ports
  // Return available port
}
```

### 5. IPC bridge between Electron and backend

Route IPC calls from renderer → main → WebSocket → Python:
```typescript
// In main process
ipcMain.handle('transcription:start', async (_, config) => {
  await backendManager.ensureRunning();
  wsClient.sendControl('start', config);
});

ipcMain.handle('transcription:stop', async () => {
  wsClient.sendControl('stop');
});
```

### 6. Error handling and recovery
- Auto-restart backend if it crashes (max 3 retries)
- Show user-friendly error if Python not found
- Fallback: offer to install Python via the app
- Log all backend output for debugging

## Production Considerations
- **Option A**: Bundle Python with the app (larger size, ~500MB, but works out of the box)
- **Option B**: Use system Python (smaller app, requires user to have Python)
- **Recommendation**: Start with Option B for dev, implement Option A for release

## Acceptance Criteria
- [ ] Backend starts when Electron app launches
- [ ] Backend stops when Electron app closes
- [ ] Health check monitors backend status
- [ ] Auto-restart on crash (with backoff)
- [ ] First-run setup detects missing dependencies
- [ ] Port conflicts are handled
- [ ] Backend logs are captured and accessible
- [ ] Error messages shown to user when backend fails
