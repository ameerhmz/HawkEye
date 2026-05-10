# Tunnel Setup (LiveKit + API)

This project runs LiveKit and APIs locally, but the dashboard is hosted on Vercel.
Use a tunnel so phones can reach your laptop securely over the internet.

## Option A: Cloudflare Tunnel (recommended)

Pros: stable, no client install on phones, free.

1. Install `cloudflared` on the laptop.
2. Create a tunnel and map a public hostname to your local LiveKit port.
3. Example config (adjust host/port):

```yaml
# ~/.cloudflared/config.yml
hostname: livekit.yourdomain.com
service: http://localhost:7880
```

4. Run the tunnel:

```bash
cloudflared tunnel run <tunnel-name>
```

5. Set `NEXT_PUBLIC_LIVEKIT_URL=https://livekit.yourdomain.com` in dashboard/.env.

## Option B: ngrok

Pros: quick to start. Cons: free URLs change.

1. Start a tunnel to LiveKit:

```bash
ngrok http 7880
```

2. Use the HTTPS URL shown by ngrok as `NEXT_PUBLIC_LIVEKIT_URL`.

## Local LiveKit config (example)

Minimal configuration for local testing:

```yaml
# livekit.yaml
port: 7880
rtc:
	port_range_start: 50000
	port_range_end: 60000
keys:
	your_key: your_secret
```

Run LiveKit with the config:

```bash
livekit-server --config livekit.yaml
```

## Install LiveKit server (no Docker)

### macOS (Homebrew)

```bash
brew install livekit
```

### Linux (binary)

1. Download the latest release from LiveKit.
2. Unpack and move the binary into your PATH.

```bash
tar -xzf livekit-server-*.tar.gz
sudo mv livekit-server /usr/local/bin/
```

## Verify LiveKit is running

After starting LiveKit, check the health endpoint:

```bash
curl http://localhost:7880/health
```

Expected response:

```json
{"status":"ok"}
```

## Notes
- LiveKit default HTTP port is often 7880; adjust if yours differs.
- Ensure the public URL maps to LiveKit's HTTP endpoint.
- Keep API keys in local .env and Vercel environment variables only.
