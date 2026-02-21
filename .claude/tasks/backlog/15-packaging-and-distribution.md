# Task 15: Packaging and Distribution

## Objective
Package the Electron + Python application for distribution on macOS, Windows, and Linux.

## Steps

### 1. Electron packaging with electron-builder

```json
// electron/package.json
{
  "build": {
    "appId": "com.opennode.app",
    "productName": "OpenNode",
    "directories": {
      "output": "dist"
    },
    "files": [
      "dist/**/*",
      "assets/**/*"
    ],
    "extraResources": [
      {
        "from": "../backend",
        "to": "backend",
        "filter": ["**/*", "!.venv/**", "!__pycache__/**", "!*.pyc"]
      }
    ],
    "mac": {
      "category": "public.app-category.productivity",
      "icon": "assets/icon.icns",
      "target": ["dmg", "zip"],
      "entitlements": "entitlements.mac.plist",
      "hardenedRuntime": true
    },
    "win": {
      "icon": "assets/icon.ico",
      "target": ["nsis", "portable"]
    },
    "linux": {
      "icon": "assets/icon.png",
      "target": ["AppImage", "deb"],
      "category": "Office"
    }
  }
}
```

### 2. macOS entitlements
```xml
<!-- entitlements.mac.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.device.audio-input</key>
    <true/>
    <key>com.apple.security.device.screen-capture</key>
    <true/>
</dict>
</plist>
```

### 3. Python bundling strategy

**Option A: System Python (recommended for v1)**
- Require Python 3.10+ pre-installed
- Create venv on first run
- Install dependencies automatically
- Pros: Smaller app size, uses system GPU drivers
- Cons: Requires Python installation

**Option B: Bundled Python (for future)**
- Bundle python-build-standalone
- ~100MB additional size
- Self-contained, no dependencies
- Use PyInstaller or cx_Freeze for the backend

### 4. Model management
- Models are NOT bundled (too large: 2.5GB+)
- Download on first run with progress bar
- Store in `~/.opennode/models/`
- Verify checksums after download

### 5. Build scripts
```json
{
  "scripts": {
    "build:mac": "electron-builder --mac",
    "build:win": "electron-builder --win",
    "build:linux": "electron-builder --linux",
    "build:all": "electron-builder -mwl"
  }
}
```

### 6. Auto-updater (future)
- Use `electron-updater` with GitHub Releases
- Check for updates on startup
- Download and install in background

### 7. GitHub Actions CI/CD
```yaml
# .github/workflows/build.yml
# Build and release on tag push
# Matrix: macOS, Windows, Linux
# Upload artifacts to GitHub Releases
```

## Acceptance Criteria
- [ ] macOS DMG builds and installs
- [ ] Windows installer works
- [ ] Linux AppImage runs
- [ ] Python backend starts from packaged app
- [ ] Model download works on first run
- [ ] App signs and notarizes on macOS
- [ ] File size is reasonable (<200MB without models)
