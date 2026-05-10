"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Room,
  RoomEvent,
  RemoteParticipant,
  RemoteTrack,
  RemoteTrackPublication
} from "livekit-client";
import { getAuthHeaders, getAuthToken } from "@/lib/auth";
import { normalizeLiveKitUrl } from "@/lib/livekit";

/* ── Types ── */

type Tile = { id: string; label: string; track: RemoteTrack };
type Camera = { id: number; name: string; location: string; status: string };
type Alert = { id: number; camera_id: number; alert_type: string; severity: string; timestamp: string; message: string; image_url?: string; };
type BoundingBox = { class: string; conf: number; x1: number; y1: number; x2: number; y2: number; track_id?: number; action?: string; dwell_time?: number };

/* ── Constants ── */

const roomUrl = normalizeLiveKitUrl(process.env.NEXT_PUBLIC_LIVEKIT_URL ?? "");
const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

/* ── Page ── */

export default function MonitorPage() {
  const roomRef = useRef<Room | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [tiles, setTiles] = useState<Tile[]>([]);
  const [status, setStatus] = useState("disconnected");
  const [error, setError] = useState<string | null>(null);
  const [roomName, setRoomName] = useState("hawkeye");
  const [viewerName, setViewerName] = useState("Security Operator");
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  
  // Track which cameras have active motion alerts
  const [flashingCameras, setFlashingCameras] = useState<Set<number>>(new Set());
  
  // Real-time bounding boxes from AI Worker via Data Channel
  const [boxesByTrack, setBoxesByTrack] = useState<Record<string, BoundingBox[]>>({});

  /* ── Audio Alarm Synth ── */
  const playAlarm = useCallback(() => {
    try {
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioContextClass) return;
      const ctx = new AudioContextClass();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      
      osc.connect(gain);
      gain.connect(ctx.destination);
      
      osc.type = "square";
      osc.frequency.setValueAtTime(880, ctx.currentTime); // A5
      osc.frequency.setValueAtTime(1108.73, ctx.currentTime + 0.2); // C#6
      
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
      
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.4);
    } catch (e) {
      console.log("Audio play blocked by browser. User must interact with page first.");
    }
  }, []);

  /* ── API data fetching + WebSocket ── */

  useEffect(() => {
    if (!apiBaseUrl) return;

    const fetchData = async () => {
      try {
        const [cameraRes, alertRes] = await Promise.all([
          fetch(`${apiBaseUrl}/camera/list`, { headers: getAuthHeaders() }),
          fetch(`${apiBaseUrl}/alerts`, { headers: getAuthHeaders() })
        ]);

        if (cameraRes.status === 401 || alertRes.status === 401) {
          setError("Login required. Visit /login.");
        }
        if (cameraRes.ok) setCameras((await cameraRes.json()) as Camera[]);
        if (alertRes.ok) setAlerts((await alertRes.json()) as Alert[]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "API error.");
      }
    };

    fetchData();
    const interval = window.setInterval(fetchData, 10000);

    const token = getAuthToken();
    const wsUrl = apiBaseUrl.replace(/^http/, "ws");
    const url = token ? `${wsUrl}/ws/alerts?token=${token}` : `${wsUrl}/ws/alerts`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (msg) => {
      try {
        const payload = JSON.parse(msg.data) as { type: string; data: Alert };
        if (payload.type === "alert") {
          const newAlert = payload.data as Alert;
          setAlerts((prev) => [newAlert, ...prev]);
          
          playAlarm(); // Sound the alarm!
          
          // Trigger visual flash for 5 seconds
          setFlashingCameras(prev => {
             const next = new Set(prev);
             next.add(newAlert.camera_id);
             return next;
          });
          
          window.setTimeout(() => {
            setFlashingCameras(prev => {
                const next = new Set(prev);
                next.delete(newAlert.camera_id);
                return next;
            });
          }, 5000);
        }
      } catch {
        // ignore malformed messages
      }
    };

    return () => {
      window.clearInterval(interval);
      if (ws.readyState === WebSocket.CONNECTING) {
        ws.onopen = () => ws.close();
      } else {
        ws.close();
      }
    };
  }, [playAlarm]);

  /* ── Track helpers ── */

  const upsertTrack = useCallback((track: RemoteTrack, participant: RemoteParticipant) => {
    if (track.kind !== "video") return;
    const id = `${participant.sid}-${track.sid}`;
    setTiles((prev) =>
      prev.some((t) => t.id === id)
        ? prev
        : [...prev, { id, label: participant.name || participant.identity, track }]
    );
  }, []);

  const removeTrack = useCallback((track: RemoteTrack, participant: RemoteParticipant) => {
    const id = `${participant.sid}-${track.sid}`;
    track.detach();
    setTiles((prev) => prev.filter((t) => t.id !== id));
    // Clean up boxes
    if (track.sid) {
       setBoxesByTrack(prev => {
          const next = { ...prev };
          delete next[track.sid as string];
          return next;
       });
    }
  }, []);

  /* ── LiveKit room ── */

  const connectToRoom = useCallback(async () => {
    setError(null);
    setStatus("connecting...");
    try {
      // Browsers require a gesture to play audio. Connecting satisfies this.
      // We play a silent click to unlock the AudioContext immediately.
      playAlarm();

      if (!roomUrl) throw new Error("LiveKit URL is required.");

      const identity = `${viewerName}-${crypto.randomUUID()}`;
      const response = await fetch("/api/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identity, name: viewerName, room: roomName, canPublish: false, canSubscribe: true })
      });
      if (!response.ok) throw new Error("Failed to fetch LiveKit token.");
      const payload = (await response.json()) as { token?: string; error?: string };
      if (!payload.token) throw new Error(payload.error ?? "Invalid token response.");

      const room = new Room();

      room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, _pub: RemoteTrackPublication, participant: RemoteParticipant) => {
        upsertTrack(track, participant);
      });

      room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack, _pub: RemoteTrackPublication, participant: RemoteParticipant) => {
        removeTrack(track, participant);
      });

      room.on(RoomEvent.ParticipantDisconnected, (participant) => {
        participant.trackPublications.forEach((pub) => {
          if (pub.track) removeTrack(pub.track, participant);
        });
      });

      // Listen for bounding boxes from AI Worker
      room.on(RoomEvent.DataReceived, (payload, _participant, _kind, topic) => {
         if (topic === "bounding_boxes") {
            try {
               const strData = new TextDecoder().decode(payload);
               const data = JSON.parse(strData) as { track_sid: string, boxes: BoundingBox[] };
               setBoxesByTrack(prev => ({ ...prev, [data.track_sid]: data.boxes }));
            } catch (e) {
               console.error("Failed parsing AI data", e);
            }
         }
      });

      await room.connect(roomUrl, payload.token);
      roomRef.current = room;
      setStatus("connected");

      room.remoteParticipants.forEach((participant) => {
        participant.trackPublications.forEach((pub) => {
          if (pub.track) upsertTrack(pub.track, participant);
        });
      });
    } catch (err) {
      setStatus("disconnected");
      setError(err instanceof Error ? err.message : "LiveKit error.");
    }
  }, [roomName, viewerName, upsertTrack, removeTrack, playAlarm]);

  const disconnectFromRoom = useCallback(() => {
    roomRef.current?.disconnect();
    roomRef.current = null;
    setTiles([]);
    setBoxesByTrack({});
    setStatus("disconnected");
  }, []);
  
  // Helper to determine if a tile is flashing based on camera mapping
  const isTileFlashing = (tileLabel: string) => {
     return Array.from(flashingCameras).some(camId => {
        const cam = cameras.find(c => c.id === camId);
        return cam && tileLabel.includes(cam.name);
     });
  };

  /* ── Render ── */

  return (
    <main className="flex h-screen w-full flex-col overflow-hidden bg-[#050505] font-sans text-fog md:flex-row">
      {/* Left Sidebar */}
      <aside className="flex w-full flex-shrink-0 flex-col border-r border-white/5 bg-[#0A0A0A] md:w-80 lg:w-96">
        <header className="flex items-center justify-between border-b border-white/5 p-6">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-ember font-display text-lg text-ink shadow-glow">
              H
            </span>
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-sky/70">Hawk Eye</p>
              <h1 className="font-display text-xl text-white">Operations center</h1>
            </div>
          </div>
          <Link href="/" className="text-xs uppercase tracking-widest text-fog/50 hover:text-white">
            Exit
          </Link>
        </header>

        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          
          {/* Room Connection */}
          <section>
            <h2 className="mb-4 text-xs font-bold uppercase tracking-[0.2em] text-fog/40">Network Status</h2>
            <div className="rounded-2xl border border-white/5 bg-[#121212] p-4 text-sm">
               <div className="flex items-center justify-between mb-4">
                  <span className="text-fog/70">LiveKit Link</span>
                  <span className={`h-2 w-2 rounded-full ${status === 'connected' ? 'bg-moss shadow-[0_0_10px_rgba(100,255,100,0.5)]' : 'bg-ember'}`}></span>
               </div>
               
               {status !== "connected" ? (
                  <button onClick={connectToRoom} className="w-full rounded-full bg-sky/10 border border-sky/20 py-2 text-xs uppercase tracking-widest text-sky hover:bg-sky/20 transition-colors">
                     Establish Connection
                  </button>
               ) : (
                  <button onClick={disconnectFromRoom} className="w-full rounded-full bg-ember/10 border border-ember/20 py-2 text-xs uppercase tracking-widest text-ember hover:bg-ember/20 transition-colors">
                     Disconnect
                  </button>
               )}
               {error && <p className="mt-3 text-xs text-ember/80">{error}</p>}
            </div>
          </section>

          {/* Camera Health */}
          <section>
            <h2 className="mb-4 text-xs font-bold uppercase tracking-[0.2em] text-fog/40">Registered Nodes ({cameras.length})</h2>
            <div className="flex flex-col gap-2">
              {cameras.length === 0 ? (
                <p className="text-xs text-fog/50">No camera nodes registered.</p>
              ) : (
                cameras.map((camera) => {
                  const isOnline = tiles.some(t => t.label.includes(camera.name) || camera.name.includes(t.label));
                  return (
                  <div key={camera.id} className={`flex items-center justify-between rounded-xl border p-3 transition-colors ${isOnline ? 'border-moss/30 bg-[#1A1A1A]' : 'border-white/5 bg-[#121212]'}`}>
                    <div className="flex flex-col">
                      <span className={`text-sm ${isOnline ? 'text-white' : 'text-fog/50'}`}>{camera.name}</span>
                      <span className="text-[10px] uppercase tracking-widest text-fog/40">{camera.location}</span>
                    </div>
                    {isOnline ? (
                       <div className="flex items-center gap-2">
                          <span className="h-1.5 w-1.5 rounded-full bg-moss shadow-[0_0_8px_rgba(16,185,129,0.8)] animate-pulse" />
                          <span className="text-[10px] font-bold uppercase tracking-widest text-moss">Online</span>
                       </div>
                    ) : (
                       <span className="text-[10px] font-bold uppercase tracking-widest text-fog/30">Offline</span>
                    )}
                  </div>
                )})
              )}
            </div>
          </section>

          {/* Alerts Timeline */}
          <section>
            <h2 className="mb-4 text-xs font-bold uppercase tracking-[0.2em] text-fog/40">Event Timeline</h2>
            <div className="flex flex-col gap-3">
              {alerts.length === 0 ? (
                <p className="text-xs text-fog/50">System clear. No recent alerts.</p>
              ) : (
                alerts.slice(0, 10).map((alert) => (
                  <div key={alert.id} className="flex gap-3 relative group/alert">
                     <div className="mt-1 flex flex-col items-center">
                        <div className="h-2 w-2 rounded-full bg-ember shadow-[0_0_8px_rgba(255,100,100,0.8)]" />
                        <div className="flex-1 w-[1px] bg-white/5 my-1" />
                     </div>
                     <div className="flex-1 pb-4">
                        <div className="flex items-center justify-between">
                           <span className="text-xs font-bold text-ember uppercase tracking-wider">{alert.alert_type}</span>
                           <span className="text-[10px] text-fog/40">{new Date(alert.timestamp).toLocaleTimeString()}</span>
                        </div>
                        <p className="text-sm text-fog/80 mt-1">{alert.message}</p>
                        {alert.image_url && (
                          <div className="mt-2 overflow-hidden rounded-lg border border-white/10 bg-black/40">
                             <img 
                                src={`${apiBaseUrl}${alert.image_url}`} 
                                alt="Detection Snapshot" 
                                className="w-full object-cover transition-transform duration-500 group-hover/alert:scale-110"
                             />
                          </div>
                        )}
                     </div>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      </aside>

      {/* Main Grid */}
      <section className="flex-1 relative bg-black/60 p-4 md:p-6 overflow-y-auto">
         <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.4)_100%)] z-0" />
         
         <div className="relative z-10 h-full w-full flex flex-col">
            <div className="flex items-center justify-between mb-4">
               <h2 className="font-display text-2xl text-white/90">Camera Feeds</h2>
               <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-moss animate-pulse" />
                  <span className="text-xs font-bold uppercase tracking-[0.2em] text-moss/80">Live</span>
               </div>
            </div>

            {tiles.length === 0 ? (
               <div className="flex-1 flex items-center justify-center border border-dashed border-white/10 rounded-3xl bg-white/5">
                  <div className="text-center">
                     <p className="text-fog/50 text-sm">No active video feeds.</p>
                     <p className="text-fog/30 text-xs mt-2">Connect to the room to subscribe to streams.</p>
                  </div>
               </div>
            ) : (
               <div className={`grid gap-4 w-full h-[calc(100%-3rem)] ${
                  tiles.length === 1 ? 'grid-cols-1' : 
                  tiles.length <= 4 ? 'grid-cols-1 md:grid-cols-2' : 
                  'grid-cols-2 md:grid-cols-3'
               }`}>
                  {tiles.map((tile) => (
                     <VideoTile 
                        key={tile.id} 
                        tile={tile} 
                        isFlashing={isTileFlashing(tile.label)} 
                        boxes={tile.track.sid ? (boxesByTrack[tile.track.sid] || []) : []}
                     />
                  ))}
               </div>
            )}
         </div>
      </section>
    </main>
  );
}

/* ── VideoTile ── */

function VideoTile({ tile, isFlashing, boxes }: { tile: Tile, isFlashing: boolean, boxes: BoundingBox[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [timeStr, setTimeStr] = useState("");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordedChunksRef = useRef<BlobPart[]>([]);

  useEffect(() => {
    if (!containerRef.current) return;

    const element = tile.track.attach();
    // Industrial look: no rounded corners, stark black background
    element.className = "h-full w-full object-cover bg-black";
    element.setAttribute("playsinline", "true");
    element.muted = true;
    containerRef.current.innerHTML = "";
    containerRef.current.appendChild(element);

    return () => {
      tile.track.detach(element);
    };
  }, [tile]);

  useEffect(() => {
     // Start clock in YYYY/MM/DD HH:MM:SS format
     const updateClock = () => {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        setTimeStr(`${year}/${month}/${day} ${hours}:${minutes}:${seconds}`);
     };
     updateClock();
     const interval = window.setInterval(updateClock, 1000);
     return () => window.clearInterval(interval);
  }, []);

  const handleRecordToggle = () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
    } else {
      if (!tile.track.mediaStreamTrack) {
        console.error("No media stream track available to record.");
        return;
      }
      try {
        const stream = new MediaStream([tile.track.mediaStreamTrack]);
        // Use webm, it's widely supported in Chrome/Firefox for MediaRecorder
        const recorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
        
        recordedChunksRef.current = [];
        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) {
            recordedChunksRef.current.push(e.data);
          }
        };
        
        recorder.onstop = () => {
          const blob = new Blob(recordedChunksRef.current, { type: 'video/webm' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          document.body.appendChild(a);
          a.style.display = 'none';
          a.href = url;
          // Generate a filename like CAM1_1778316499.webm
          a.download = `${tile.label.replace(/\s+/g, '_')}_${Date.now()}.webm`;
          a.click();
          window.URL.revokeObjectURL(url);
        };

        recorder.start();
        mediaRecorderRef.current = recorder;
        setIsRecording(true);
      } catch (err) {
        console.error("Error starting recording:", err);
      }
    }
  };

  return (
    <div className={`group relative h-full w-full overflow-hidden border-2 transition-colors duration-300 bg-black ${
       isFlashing ? 'border-ember shadow-[0_0_30px_rgba(255,100,100,0.3)]' : 'border-white/20'
    }`}>
      {/* Container for the actual video element */}
      <div ref={containerRef} className="h-full w-full opacity-90 grayscale-[20%] contrast-125" />
      
      {/* CCTV UI Overlays */}
      <div className="absolute inset-0 pointer-events-none">
        
        {/* Center Crosshairs */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center justify-center opacity-40">
           <div className="absolute h-10 w-[1px] bg-white/60"></div>
           <div className="absolute h-[1px] w-10 bg-white/60"></div>
           <div className="h-4 w-4 rounded-full border border-white/60"></div>
        </div>

        {/* Corner Brackets */}
        <div className="absolute top-4 left-4 w-6 h-6 border-t-2 border-l-2 border-white/50 opacity-70"></div>
        <div className="absolute top-4 right-4 w-6 h-6 border-t-2 border-r-2 border-white/50 opacity-70"></div>
        <div className="absolute bottom-4 left-4 w-6 h-6 border-b-2 border-l-2 border-white/50 opacity-70"></div>
        <div className="absolute bottom-4 right-4 w-6 h-6 border-b-2 border-r-2 border-white/50 opacity-70"></div>
        
        {/* AI Bounding Boxes */}
        {boxes.map((box, i) => {
           const isDanger = box.action === 'FALLING!' || box.action === 'INTRUDER!';
           const isWarn = box.action === 'RUNNING!' || box.action === 'LOITERING';
           
           const borderColor = isDanger ? 'border-red-500' : isWarn ? 'border-orange-500' : 'border-emerald-400';
           const textColor = isDanger ? 'text-red-500' : isWarn ? 'text-orange-500' : 'text-emerald-400';
           const shadowColor = isDanger ? 'shadow-[0_0_10px_rgba(239,68,68,0.5)]' : isWarn ? 'shadow-[0_0_10px_rgba(249,115,22,0.5)]' : 'shadow-[0_0_10px_rgba(16,185,129,0.3)]';
           const bgColor = isDanger ? 'bg-red-500/20' : isWarn ? 'bg-orange-500/20' : 'bg-emerald-400/20';
           
           return (
           <div 
              key={i}
              className={`absolute border ${borderColor} ${shadowColor} transition-all duration-300`}
              style={{
                 left: `${box.x1 * 100}%`,
                 top: `${box.y1 * 100}%`,
                 width: `${(box.x2 - box.x1) * 100}%`,
                 height: `${(box.y2 - box.y1) * 100}%`,
              }}
           >
              {/* Corner accents for bounding box */}
              <div className={`absolute top-0 left-0 w-2 h-2 border-t-2 border-l-2 ${borderColor}`}></div>
              <div className={`absolute top-0 right-0 w-2 h-2 border-t-2 border-r-2 ${borderColor}`}></div>
              <div className={`absolute bottom-0 left-0 w-2 h-2 border-b-2 border-l-2 ${borderColor}`}></div>
              <div className={`absolute bottom-0 right-0 w-2 h-2 border-b-2 border-r-2 ${borderColor}`}></div>
              
              <span className={`absolute -top-5 left-[-1px] ${bgColor} ${textColor} backdrop-blur-sm px-1 py-0.5 font-mono text-[9px] font-bold tracking-widest whitespace-nowrap`}>
                 {box.action && box.action !== 'TRACKING' ? `[${box.action}] ` : ''}ID:{box.track_id} {box.dwell_time !== undefined ? `${box.dwell_time}s ` : ''}{Math.round(box.conf * 100)}%
              </span>
           </div>
        )})}
      </div>
      
      {/* Top Overlay: Camera Info & Timestamp */}
      <div className="absolute left-6 top-6 right-6 flex items-start justify-between pointer-events-none">
         <div className="flex flex-col drop-shadow-md">
            <span className="font-mono text-sm font-bold tracking-widest text-white/90">
               CAM_01 / {tile.label.toUpperCase()}
            </span>
            <span className="font-mono text-xs text-white/70">
               {timeStr}
            </span>
         </div>
         {isRecording && (
            <div className="flex items-center gap-2 drop-shadow-md bg-black/40 px-2 py-1 rounded">
               <span className="h-2 w-2 rounded-full bg-ember animate-pulse shadow-[0_0_10px_rgba(255,0,0,1)]" />
               <span className="font-mono text-[10px] font-bold tracking-widest text-ember">REC</span>
            </div>
         )}
      </div>

      {/* Motion Warning Overlay */}
      {isFlashing && (
         <div className="absolute bottom-6 left-1/2 -translate-x-1/2 pointer-events-none">
            <div className="bg-ember/20 backdrop-blur-[2px] border border-ember/50 px-4 py-1">
               <span className="font-mono text-[10px] font-bold tracking-widest text-ember animate-pulse">
                  MOTION DETECTED
               </span>
            </div>
         </div>
      )}

      {/* Hover Controls */}
      <div className="absolute bottom-6 right-6 opacity-0 transition-opacity duration-200 group-hover:opacity-100 z-20">
         <button 
            onClick={handleRecordToggle} 
            className={`px-3 py-1.5 font-mono text-[10px] font-bold tracking-widest transition-all ${
               isRecording 
               ? 'bg-ember/20 text-white border border-ember hover:bg-ember/40' 
               : 'bg-black/60 text-white/80 border border-white/30 hover:bg-white/10 hover:text-white'
            }`}
         >
            {isRecording ? "STOP REC" : "START REC"}
         </button>
      </div>
    </div>
  );
}
