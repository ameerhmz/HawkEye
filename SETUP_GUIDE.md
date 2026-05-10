# Hawk Eye Setup Guide

A step-by-step guide to set up Hawk Eye - AI-Powered Surveillance System on your machine.

## 📋 Prerequisites

Before running the setup script, ensure you have these installed:

### Required
- **Python 3.10+**: [Download](https://www.python.org/downloads/)
- **Node.js 18+**: [Download](https://nodejs.org/)

### Recommended (for full functionality)
- **PostgreSQL**: Required for database. [Download](https://www.postgresql.org/download/)
- **LiveKit Server**: For WebRTC streaming. `brew install livekit` (Mac) or [Download](https://github.com/livekit/livekit-server)
- **Cloudflared**: For secure tunneling. `brew install cloudflared` (Mac) or [Download](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)

## 🚀 Quick Start

### For Mac/Linux Users

1. **Clone the repository from GitHub**:
   ```bash
   git clone <repository-url>
   cd CCTV
   ```

2. **Run the setup script**:
   ```bash
   ./setup.sh
   ```

3. **Configure environment files** (provided separately by the project owner):
   - Create `backend/.env` with your settings
   - Create `dashboard/.env.local` with your settings

4. **Start the system**:
   ```bash
   source .venv/bin/activate
   ./scripts/dev.sh
   ```

### For Windows Users (Option 1: Batch File)

1. **Clone the repository from GitHub**:
   ```cmd
   git clone <repository-url>
   cd CCTV
   ```

2. **Run the setup script**:
   ```cmd
   setup.bat
   ```

3. **Configure environment files** (provided separately by the project owner):
   - Create `backend\.env` with your settings
   - Create `dashboard\.env.local` with your settings

4. **Start the system**:
   ```cmd
   .venv\Scripts\activate.bat
   scripts\dev.bat
   ```

### For Windows Users (Option 2: PowerShell)

1. **Clone the repository from GitHub**:
   ```powershell
   git clone <repository-url>
   cd CCTV
   ```

2. **Run the setup script**:
   ```powershell
   .\setup.ps1
   ```

   *If you get an execution policy error, run*:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. **Configure environment files** (provided separately by the project owner):
   - Create `backend\.env` with your settings
   - Create `dashboard\.env.local` with your settings

4. **Start the system**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   .\scripts\dev.bat
   ```

## 📦 What the Setup Script Does

The setup scripts (`setup.sh`, `setup.bat`, or `setup.ps1`) automatically:

1. ✓ Checks for Python and Node.js installations
2. ✓ Creates a Python virtual environment (`.venv`)
3. ✓ Installs all Python dependencies from `backend/requirements.txt`
4. ✓ Installs all Node.js dependencies from `dashboard/package.json`
5. ✓ Creates required directories:
   - `logs/` - for application logs
   - `backend/static/snapshots/` - for captured snapshots
   - `static/snapshots/` - for shared snapshots
6. ✓ Checks for environment configuration files
7. ✓ Provides next steps and usage instructions

## 🔧 Environment Configuration

Your friend will need to create two environment files. These are **NOT** included in the repository for security reasons:

### `backend/.env`
Contains backend configuration (database, API keys, etc.)

### `dashboard/.env.local`
Contains dashboard configuration (API endpoints, LiveKit settings, etc.)

*The project owner should provide these files or a template.*

## 🐍 Virtual Environment

The setup script creates a Python virtual environment in the `.venv` directory.

### Activate it manually (if needed):

**Mac/Linux:**
```bash
source .venv/bin/activate
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

### Deactivate it:
```bash
deactivate
```

## 📝 Project Structure

```
.
├── setup.sh              # Mac/Linux setup script
├── setup.bat             # Windows batch setup script
├── setup.ps1             # Windows PowerShell setup script
├── scripts/
│   ├── dev.sh            # Mac/Linux master orchestration script
│   ├── dev.ps1           # Windows PowerShell master orchestration script
│   └── dev.bat           # Windows batch wrapper
├── backend/              # FastAPI backend
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   └── ...
│   └── static/
├── dashboard/            # Next.js frontend
│   ├── package.json
│   ├── app/
│   │   ├── page.tsx
│   │   ├── layout.tsx
│   │   └── ...
│   └── node_modules/     # (created by npm install)
└── logs/                 # (created by setup)
```

## 🐛 Troubleshooting

### Python not found
- Ensure Python 3.10+ is installed and in your PATH
- On Mac, you may need to use `python3` instead of `python`

### Node.js not found
- Ensure Node.js 18+ is installed and in your PATH
- Verify with `node --version` and `npm --version`

### Virtual environment fails to create
- Ensure you have write permissions in the project directory
- Try deleting `.venv` and running the setup script again

### npm install fails
- Delete `dashboard/node_modules` and `dashboard/package-lock.json`
- Run the setup script again or manually run `npm install` in the `dashboard/` directory

### Missing environment files
- Verify you have `backend/.env` and `dashboard/.env.local` files
- Contact the project owner for the environment configuration templates

## 📚 More Information

- See [README.md](README.md) for project overview and running instructions
- See [BEHAVIOR_DETECTION_GUIDE.md](BEHAVIOR_DETECTION_GUIDE.md) for AI detection configuration
- See [plan.md](plan.md) for project architecture and milestones

## 🆘 Getting Help

If you encounter issues:

1. Check this troubleshooting section
2. Review the error messages carefully
3. Ensure all prerequisites are installed
4. Contact the project owner with details about your error
