import { spawn, ChildProcess } from 'child_process'
import path from 'path'
import fs from 'fs'
import { EventEmitter } from 'events'
import { app } from 'electron'

export interface EnvironmentStatus {
  pythonPath: string | null
  pythonVersion: string | null
  packagesInstalled: boolean
  gpuAvailable: boolean
  gpuName: string | null
  diskSpaceGB: number
}

export interface BackendStatus {
  running: boolean
  ready: boolean
  port: number
  pid: number | null
}

export class BackendManager extends EventEmitter {
  private process: ChildProcess | null = null
  private _port: number
  private _isReady = false
  private _restartCount = 0
  private readonly maxRestarts = 3
  private _logLines: string[] = []
  private readonly maxLogLines = 1000

  constructor(port = 8765) {
    super()
    this._port = port
  }

  get port(): number { return this._port }
  get isReady(): boolean { return this._isReady }
  get pid(): number | null { return this.process?.pid ?? null }
  get logs(): string[] { return [...this._logLines] }

  /** Find an available port starting from preferred. */
  async findAvailablePort(preferred = 8765): Promise<number> {
    const net = await import('net')
    return new Promise((resolve) => {
      const server = net.createServer()
      server.listen(preferred, () => {
        const addr = server.address() as { port: number }
        server.close(() => resolve(addr.port))
      })
      server.on('error', () => resolve(this.findAvailablePort(preferred + 1)))
    })
  }

  /** Locate Python executable: venv > system python3 > python */
  async findPython(): Promise<string | null> {
    const candidates: string[] = []

    // 1. Venv in backend dir (dev)
    const backendDir = this.getBackendDir()
    if (backendDir) {
      const venvPy = process.platform === 'win32'
        ? path.join(backendDir, '.venv', 'Scripts', 'python.exe')
        : path.join(backendDir, '.venv', 'bin', 'python')
      candidates.push(venvPy)
    }

    // 2. Bundled Python (production — next to app binary)
    const bundledPy = process.platform === 'win32'
      ? path.join(app.getPath('exe'), '..', 'python', 'python.exe')
      : path.join(app.getPath('exe'), '..', 'python', 'bin', 'python3')
    candidates.push(bundledPy)

    // 3. System python
    candidates.push('python3', 'python')

    for (const candidate of candidates) {
      if (await this._pythonWorks(candidate)) return candidate
    }
    return null
  }

  private async _pythonWorks(pyPath: string): Promise<boolean> {
    try {
      if (pyPath !== 'python3' && pyPath !== 'python' && !fs.existsSync(pyPath)) return false
      const { execFile } = await import('child_process')
      const { promisify } = await import('util')
      const execFileAsync = promisify(execFile)
      await execFileAsync(pyPath, ['--version'])
      return true
    } catch {
      return false
    }
  }

  private getBackendDir(): string | null {
    // In dev: project root / backend
    // In prod: resourcesPath / backend
    const dev = path.join(app.getAppPath(), '..', 'backend')
    if (fs.existsSync(dev)) return dev
    const prod = path.join(process.resourcesPath ?? '', 'backend')
    if (fs.existsSync(prod)) return prod
    return null
  }

  async checkEnvironment(): Promise<EnvironmentStatus> {
    const pythonPath = await this.findPython()
    let pythonVersion: string | null = null
    let packagesInstalled = false
    let gpuAvailable = false
    let gpuName: string | null = null

    if (pythonPath) {
      try {
        const { execFile } = await import('child_process')
        const { promisify } = await import('util')
        const execFileAsync = promisify(execFile)
        const { stdout: ver } = await execFileAsync(pythonPath, ['--version'])
        pythonVersion = ver.trim().replace('Python ', '')

        const { stdout: pkgCheck } = await execFileAsync(pythonPath, [
          '-c', 'import opennode; print("ok")'
        ]).catch(() => ({ stdout: '' }))
        packagesInstalled = pkgCheck.trim() === 'ok'

        const { stdout: gpuCheck } = await execFileAsync(pythonPath, [
          '-c',
          'import subprocess, json; r=subprocess.run(["nvidia-smi","--query-gpu=name","--format=csv,noheader"],capture_output=True,text=True); print(r.stdout.strip() if r.returncode==0 else "")'
        ]).catch(() => ({ stdout: '' }))
        if (gpuCheck.trim()) { gpuAvailable = true; gpuName = gpuCheck.trim().split('\n')[0] }
      } catch { /* ignore */ }
    }

    // Disk space
    let diskSpaceGB = 0
    try {
      const { execFile } = await import('child_process')
      const { promisify } = await import('util')
      const execFileAsync = promisify(execFile)
      if (process.platform !== 'win32') {
        const { stdout } = await execFileAsync('df', ['-k', app.getPath('home')])
        const lines = stdout.trim().split('\n')
        const cols = lines[lines.length - 1].split(/\s+/)
        diskSpaceGB = parseInt(cols[3] ?? '0') / 1024 / 1024
      }
    } catch { /* ignore */ }

    return { pythonPath, pythonVersion, packagesInstalled, gpuAvailable, gpuName, diskSpaceGB }
  }

  async start(): Promise<void> {
    if (this.process) return

    this._port = await this.findAvailablePort(this._port)
    const pythonPath = await this.findPython()
    if (!pythonPath) {
      this.emit('error', 'Python not found. Please install Python 3.10+ and the opennode package.')
      return
    }

    const backendDir = this.getBackendDir()
    const env = { ...process.env, OPENNODE_PORT: String(this._port), PYTHONUNBUFFERED: '1' }

    this.process = spawn(pythonPath, ['-m', 'opennode'], {
      cwd: backendDir ?? undefined,
      env,
      stdio: ['pipe', 'pipe', 'pipe'],
    })

    this.process.stdout?.on('data', (data: Buffer) => {
      const text = data.toString()
      this._appendLog(text)
      if (text.includes('Application startup complete') || text.includes('Uvicorn running')) {
        this._isReady = true
        this.emit('ready', this._port)
      }
    })

    this.process.stderr?.on('data', (data: Buffer) => {
      const text = data.toString()
      this._appendLog(text)
      // uvicorn logs to stderr
      if (text.includes('Application startup complete') || text.includes('Uvicorn running')) {
        this._isReady = true
        this.emit('ready', this._port)
      }
    })

    this.process.on('exit', (code) => {
      this._isReady = false
      this.process = null
      if (code !== 0 && this._restartCount < this.maxRestarts) {
        this._restartCount++
        const delay = Math.min(1000 * 2 ** this._restartCount, 30_000)
        this.emit('restarting', { attempt: this._restartCount, delay })
        setTimeout(() => this.start().catch(console.error), delay)
      } else {
        this.emit('stopped', code)
      }
    })

    // Wait for ready with 60s timeout (model loading can be slow)
    await this._waitForReady(60_000)
  }

  private async _waitForReady(timeoutMs: number): Promise<void> {
    return new Promise((resolve) => {
      if (this._isReady) { resolve(); return }
      const timer = setTimeout(() => {
        // Try health check even if we didn't see the startup message
        this.checkHealth().then(ok => {
          if (ok) { this._isReady = true; this.emit('ready', this._port) }
          resolve()
        })
      }, timeoutMs)
      this.once('ready', () => { clearTimeout(timer); resolve() })
    })
  }

  async checkHealth(): Promise<boolean> {
    try {
      const res = await fetch(`http://127.0.0.1:${this._port}/health`, { signal: AbortSignal.timeout(3000) })
      return res.ok
    } catch { return false }
  }

  async stop(): Promise<void> {
    if (!this.process) return
    this._restartCount = this.maxRestarts // prevent auto-restart
    this.process.kill('SIGTERM')
    await new Promise<void>((resolve) => {
      const t = setTimeout(() => { this.process?.kill('SIGKILL'); resolve() }, 5000)
      this.process!.once('exit', () => { clearTimeout(t); resolve() })
    })
    this.process = null
    this._isReady = false
  }

  getStatus(): BackendStatus {
    return { running: !!this.process, ready: this._isReady, port: this._port, pid: this.pid }
  }

  private _appendLog(text: string): void {
    const lines = text.split('\n').filter(Boolean)
    this._logLines.push(...lines)
    if (this._logLines.length > this.maxLogLines) {
      this._logLines = this._logLines.slice(-this.maxLogLines)
    }
    this.emit('log', lines)
  }
}

export const backendManager = new BackendManager()
