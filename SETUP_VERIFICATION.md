# ✅ Setup Verification Checklist

Use this checklist to verify that the setup was completed successfully.

## Pre-Setup Requirements

- [ ] Python 3.10+ installed (`python --version` shows 3.10+)
- [ ] Node.js 18+ installed (`node --version` shows 18+)
- [ ] npm installed (`npm --version` works)
- [ ] Git installed (cloned repository successfully)
- [ ] Terminal/Command Prompt open in project root directory

## During Setup

- [ ] Ran setup script without errors (setup.sh / setup.bat / setup.ps1)
- [ ] Virtual environment created (.venv folder exists)
- [ ] Backend dependencies installed
- [ ] Dashboard dependencies installed
- [ ] Required directories created (logs/, backend/static/snapshots/, etc.)

## Post-Setup Configuration

- [ ] Received `backend/.env` file from project owner
- [ ] Received `dashboard/.env.local` file from project owner
- [ ] Placed `backend/.env` in project root
- [ ] Placed `dashboard/.env.local` in project root
- [ ] Environment files contain valid configuration

## Verification Steps

### ✅ Check Python Setup
```bash
source .venv/bin/activate          # Mac/Linux
# or
.venv\Scripts\activate.bat         # Windows CMD
# or
.\.venv\Scripts\Activate.ps1       # Windows PowerShell

python --version
pip list | head -10
```
Should show Python 3.10+ and FastAPI, SQLAlchemy, etc. in pip list.

### ✅ Check Node Setup
```bash
node --version
npm --version
cd dashboard && npm list | head -10
cd ..
```
Should show Node 18+ and packages like react, next, livekit-client.

### ✅ Check File Structure
```bash
ls -la backend/static/snapshots/
ls -la static/snapshots/
ls -la logs/
```
These folders should exist and be empty (or with existing data).

### ✅ Check Environment Files
```bash
ls -la backend/.env
ls -la dashboard/.env.local
```
Both files should exist.

### ✅ Check Virtual Environment
```bash
which python             # Mac/Linux - should be in .venv
# or
where python            # Windows - should be in .venv
```

## Final Checks

- [ ] Can activate virtual environment without errors
- [ ] Backend dependencies are importable
- [ ] Dashboard can be started: `cd dashboard && npm run dev`
- [ ] Backend can be started: `cd backend && uvicorn app.main:app --reload`
- [ ] No error messages during imports
- [ ] .gitignore properly excludes .env files

## Ready to Start?

- [ ] All checks above passed
- [ ] Ready to run `./scripts/dev.sh` (Mac/Linux) or `.\scripts\dev.sh` (Windows)

## 🆘 Troubleshooting

If any check fails:

1. **Check the error message carefully**
2. **Refer to SETUP_GUIDE.md troubleshooting section**
3. **Try running the setup script again:**
   - Mac/Linux: `./setup.sh`
   - Windows: `setup.bat` or `.\setup.ps1`
4. **Contact project owner with error details**

## 📝 Setup Completed!

If all checks passed, your setup is complete! 🎉

Next steps:
1. Activate the virtual environment (if not already)
2. Run the development server
3. Open the dashboard in your browser

For more details, see FRIEND_SETUP_GUIDE.md or README.md.
