# Hawk Eye - Project Plan

## Goals
- Run all AI processing locally on a single laptop.
- Deploy the dashboard to Vercel so phones can access it over the internet.
- Deliver a working end-to-end demo with live camera nodes, detection, alerts, and dashboard.

## Scope Simplifications
- AI and core services remain on the laptop only.
- Frontend hosted on Vercel for remote access.
- No GPU requirement (CPU-first; optional GPU later).
- Advanced AI features deferred (face, fire/smoke, weapon).
- Minimum of 3-5 camera nodes for testing.
- Keep monitoring lightweight (basic logs + simple metrics).

## Architecture (Simplified)
- Smartphone browsers -> WebRTC -> LiveKit (local)
- FastAPI AI service (local)
- Realtime Gateway (local)
- Next.js Dashboard (Vercel)
- PostgreSQL + Redis (local)
- Secure ingress to local services (tunnel or reverse proxy)

## Vercel Access Plan
- Use a secure tunnel from the laptop to expose LiveKit and API endpoints.
- Prefer a single public base URL for the dashboard to reach local services.
- Restrict access with auth tokens and IP allowlists when possible.
- Keep private keys and secrets in Vercel env vars and local .env only.

## Milestones
1. Baseline streaming
   - LiveKit running locally
   - Vercel dashboard reachable from phones
   - Camera page connects and streams to local LiveKit
   - Dashboard shows at least 2 live feeds
   - Public tunnel stable for at least 1 hour

2. AI detection pipeline (local)
   - Frame capture from stream
   - YOLOv8 person detection
   - Basic motion detection
   - Event generation to DB

3. Events + alerts
   - Event log API
   - Realtime updates in dashboard
   - Basic alert rule for intrusion zone

4. Recording + snapshots
   - Event-based clip saving
   - Snapshot saved per detection
   - Playback in dashboard

5. Hardening + polish
   - Reconnect handling
   - Simple role-based access control
   - Minimal metrics and logs

## Deliverables
- Working local stack with Docker Compose
- Vercel dashboard with live view, alerts, timeline
- AI detection running on laptop
- Documentation for setup and run
