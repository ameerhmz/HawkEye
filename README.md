# Hawk Eye: AI-Powered Surveillance System 🚀

Hawk Eye is a professional-grade, local-first surveillance system that combines real-time AI object detection (YOLOv8) with high-performance video streaming (LiveKit) and automated secure tunneling (Cloudflare).

## 🛠 Prerequisites

Before you begin, ensure you have the following installed on your laptop (Mac/Linux):

1.  **Python 3.10+**: For the AI Worker and FastAPI Backend.
2.  **Node.js 18+**: For the Next.js Dashboard.
3.  **LiveKit Server**: For real-time WebRTC video streaming.
    *   `brew install livekit` (Mac)
4.  **Cloudflared**: For automated secure tunneling.
    *   `brew install cloudflared` (Mac)
5.  **PostgreSQL**: The backend uses Postgres for alert persistence.

## 📦 First-Time Setup

### 1. Clone & Dependencies
```bash
# Install Python dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Install Dashboard dependencies
cd dashboard
npm install
cd ..
```

### 2. Configuration
Ensure your `backend/.env` and `dashboard/.env` files are configured. The system is designed to **automatically** update the Dashboard URLs for you during startup.

## 🚀 Running the App

To start the entire infrastructure (Backend, AI Worker, LiveKit, Dashboard, and Tunnels) with one command, simply run:

```bash
./scripts/dev.sh
```

### What happens when you run this?
1.  **Tunneling**: It starts 3 Cloudflare tunnels to expose your local services to the internet securely.
2.  **Auto-Config**: It automatically grabs the new `trycloudflare.com` URLs and updates your `dashboard/.env`.
3.  **Services**: It boots the FastAPI Backend, LiveKit Server, Next.js Dashboard, and the YOLOv8 AI Worker.
4.  **Live Links**: It prints your unique Dashboard and API links directly to the terminal.

## 📱 Usage

1.  **Open the Dashboard**: Visit the generated Dashboard URL on your laptop.
2.  **Connect a Phone**: Visit the Dashboard URL `/camera` on your phone (e.g., `https://random-slug.trycloudflare.com/camera`).
3.  **Monitor**: On your laptop, click **"Establish Connection"**.
4.  **AI Tracking**: The AI worker will track persons at 3 FPS and draw emerald green bounding boxes.
5.  **Alerts**: If a person is detected, the dashboard will flash red and play a synthesized security alarm.

## 🧹 Resetting Camera Data

If you want to remove previous camera registrations and stored snapshot images, run:

```bash
.venv/bin/python backend/scripts/reset_camera_data.py --no-dry-run
```

This clears camera rows, related alerts/events/recordings, and snapshot files from both snapshot folders.

## 📂 Project Structure

*   `dashboard/`: Next.js Frontend with Web Audio API and LiveKit Data Channel integration.
*   `backend/`: FastAPI server handling camera registration and alert persistence.
*   `backend/worker.py`: The AI engine running YOLOv8 inference and publishing tracking data.
*   `scripts/dev.sh`: The master orchestration script.
*   `logs/`: Real-time logs for all services.

## 🛑 Stopping
To stop all services, simply press `Ctrl+C` in the terminal where `dev.sh` is running, or run:
```bash
pkill -f 'uvicorn|livekit|next|worker.py|cloudflared'
```
