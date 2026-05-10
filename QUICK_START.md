# 🚀 Quick Setup Instructions

Welcome! Follow these steps to get Hawk Eye running on your machine.

## Step 1: Prerequisites
Make sure you have installed:
- **Python 3.10+** → [Download](https://www.python.org/downloads/)
- **Node.js 18+** → [Download](https://nodejs.org/)

## Step 2: Run the Setup Script

### 🍎 Mac/Linux:
```bash
./setup.sh
```

### 🪟 Windows (Batch):
```cmd
setup.bat
```

### 🪟 Windows (PowerShell):
```powershell
.\setup.ps1
```

The script will automatically:
- ✓ Check for required tools
- ✓ Create Python virtual environment
- ✓ Install all dependencies
- ✓ Set up the project structure

## Step 3: Add Environment Files

Ask the project owner for:
- `backend/.env`
- `dashboard/.env.local`

Then place them in the project root.

## Step 4: Start the System

```bash
source .venv/bin/activate    # Mac/Linux
# or
.venv\Scripts\activate.bat    # Windows (Batch)
# or
.\.venv\Scripts\Activate.ps1  # Windows (PowerShell)

./scripts/dev.sh              # Start all services
```

---

## 📖 For More Details
See [SETUP_GUIDE.md](SETUP_GUIDE.md) for comprehensive setup instructions and troubleshooting.

---

**Stuck?** Check [SETUP_GUIDE.md#troubleshooting](SETUP_GUIDE.md#troubleshooting) or contact the project owner.
