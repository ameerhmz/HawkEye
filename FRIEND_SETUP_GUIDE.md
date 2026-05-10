# 📦 For Your Friend: Hawk Eye Setup Instructions

Hi! This guide explains how to set up this project after cloning it from GitHub.

## What You Need

Before starting, install these on your computer:

1. **Python 3.10 or newer**
   - [Download Python](https://www.python.org/downloads/)
   - **Windows**: Make sure to check ✓ "Add Python to PATH" during installation
   - **Mac**: Can use `brew install python3`

2. **Node.js 18 or newer**
   - [Download Node.js](https://nodejs.org/)
   - This includes `npm` automatically

3. **Optional but Recommended:**
   - PostgreSQL database (see README.md)
   - LiveKit (for streaming)
   - Cloudflared (for tunneling)

## How to Set Up

### 1️⃣ Clone the Repository
```bash
git clone <repository-url>
cd CCTV
```

### 2️⃣ Run the Automated Setup

Choose based on your operating system:

**Mac/Linux:**
```bash
./setup.sh
```

**Windows - Option A (Batch file):**
```cmd
setup.bat
```

**Windows - Option B (PowerShell):**
```powershell
.\setup.ps1
```

The script will:
- ✅ Check that Python and Node.js are installed
- ✅ Create a Python virtual environment
- ✅ Install all Python dependencies
- ✅ Install all Node.js/Dashboard dependencies
- ✅ Create necessary folders
- ✅ Show you the next steps

### 3️⃣ Add Environment Files

The project owner will give you these files:
- `backend/.env` - Backend configuration
- `dashboard/.env.local` - Dashboard configuration

Create these files in the project root directory with the content provided.

**⚠️ Important:** These files contain sensitive information and should NEVER be added to Git.

### 4️⃣ Run the Application

Activate the virtual environment:

**Mac/Linux:**
```bash
source .venv/bin/activate
```

**Windows - Command Prompt:**
```cmd
.venv\Scripts\activate.bat
```

**Windows - PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
```

Then start all services:
```bash
./scripts/dev.sh
```

## 📂 Important Files & Folders

- `setup.sh` - Setup script for Mac/Linux
- `setup.bat` - Setup script for Windows (Batch)
- `setup.ps1` - Setup script for Windows (PowerShell)
- `QUICK_START.md` - Quick reference guide
- `SETUP_GUIDE.md` - Detailed troubleshooting
- `README.md` - Project overview
- `backend/` - Backend API code
- `dashboard/` - Frontend code
- `.venv/` - Python virtual environment (created by setup)
- `node_modules/` - Node packages (created by npm install)

## ⚠️ What NOT to Commit to Git

These are automatically ignored by `.gitignore`:
- `.env` and `.env.*` files (environment secrets)
- `.venv/` folder (virtual environment)
- `node_modules/` folder (dependencies)
- `__pycache__/` and `.pyc` files
- `.log` files
- `.DS_Store` (Mac only)

**Never commit these to Git!**

## 🆘 Having Issues?

1. **Python/Node.js not found?**
   - Make sure they're installed and added to PATH
   - Test with: `python --version` and `node --version`

2. **Setup script fails?**
   - Check SETUP_GUIDE.md for troubleshooting
   - Ensure you're running the script from the project root directory

3. **Missing environment files?**
   - Ask the project owner for `backend/.env` and `dashboard/.env.local`

4. **Other issues?**
   - See SETUP_GUIDE.md for more troubleshooting
   - Contact the project owner with error details

## 📚 Learn More

- **Quick overview:** Read QUICK_START.md
- **Detailed setup:** Read SETUP_GUIDE.md
- **Project info:** Read README.md
- **AI detection details:** Read BEHAVIOR_DETECTION_GUIDE.md

---

**That's it!** After running the setup script and adding the env files, you're ready to go. Happy coding! 🚀
