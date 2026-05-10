"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Room } from "livekit-client";
import { getAuthHeaders } from "@/lib/auth";
import { normalizeLiveKitUrl } from "@/lib/livekit";

type CameraStatus = "idle" | "connecting" | "active" | "error";

const livekitUrl = normalizeLiveKitUrl(
  process.env.NEXT_PUBLIC_LIVEKIT_URL ?? ""
);
const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export default function CameraPage() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const roomRef = useRef<Room | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  
  const [status, setStatus] = useState<CameraStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  
  const [cameraName, setCameraName] = useState("CAM_01");
  const [location, setLocation] = useState("Main Entrance");
  const [roomName, setRoomName] = useState("hawkeye");
  const [nodeId, setNodeId] = useState<string>("");
  const [timeStr, setTimeStr] = useState("");

  // Load or generate persistent node ID
  useEffect(() => {
    let id = localStorage.getItem("hawkeye_node_id");
    if (!id) {
      id = crypto.randomUUID().split('-')[0].toUpperCase();
      localStorage.setItem("hawkeye_node_id", id);
    }
    setNodeId(id);
  }, []);

  useEffect(() => {
    if (!nodeId) return;
    setCameraName((prev) => (prev === "CAM_01" ? `CAM_${nodeId}` : prev));
  }, [nodeId]);

  // Clock
  useEffect(() => {
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

  useEffect(() => {
    return () => {
      roomRef.current?.disconnect();
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const handleActivate = async () => {
    setError(null);
    setStatus("connecting");

    try {
      if (!livekitUrl) throw new Error("LiveKit URL is required.");

      // 1. Get Camera Stream
      let stream = streamRef.current;
      if (!stream) {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
          audio: false
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      }

      // 2. Register with Backend first so we have a canonical name
      if (apiBaseUrl) {
        // Try registering with current cameraName; on 409 append nodeId and retry once
        let finalName = cameraName;
        const attemptRegister = async (name: string) => {
          return await fetch(`${apiBaseUrl}/camera/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json", ...getAuthHeaders() },
            body: JSON.stringify({ name, location, stream_url: livekitUrl }),
          });
        };

        let regRes = await attemptRegister(finalName);
        if (!regRes.ok) {
          if (regRes.status === 409) {
            finalName = `${cameraName}-${nodeId}`;
            setCameraName(finalName);
            regRes = await attemptRegister(finalName);
          }
        }
        if (!regRes.ok) {
          if (regRes.status === 401) throw new Error("Login required. Visit /login.");
          throw new Error("Failed to register camera.");
        }
      }

      // 3. Connect to LiveKit using the final registered name
      const identity = `${cameraName}-${nodeId}`;
      const response = await fetch("/api/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          identity,
          name: cameraName,
          room: roomName,
          metadata: { location },
          canPublish: true,
          canSubscribe: false,
        }),
      });

      if (!response.ok) throw new Error("Failed to fetch LiveKit token.");
      const payload = (await response.json()) as { token?: string; error?: string };
      if (!payload.token) throw new Error(payload.error ?? "Invalid token response.");

      const room = new Room();
      await room.connect(livekitUrl, payload.token);

      const videoTrack = stream?.getVideoTracks()[0];
      if (!videoTrack) throw new Error("No camera track available.");
      await room.localParticipant.publishTrack(videoTrack, { name: cameraName });

      roomRef.current = room;

      setStatus("active");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Activation failed.");
      
      // Cleanup on failure
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      roomRef.current?.disconnect();
      roomRef.current = null;
      if (videoRef.current) videoRef.current.srcObject = null;
    }
  };

  const handleDeactivate = () => {
    roomRef.current?.disconnect();
    roomRef.current = null;
    
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    
    if (videoRef.current) videoRef.current.srcObject = null;
    
    setStatus("idle");
  };

  return (
    <main className="flex h-screen w-full flex-col bg-[#050505] font-sans text-fog md:flex-row">
      {/* Left Sidebar: Controls */}
      <aside className="flex w-full flex-shrink-0 flex-col border-r border-white/10 bg-[#0A0A0A] md:w-80 z-10">
        <header className="flex items-center justify-between border-b border-white/10 p-6">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-none bg-emerald-500 font-display text-lg text-black font-bold">
              TX
            </span>
            <div>
              <p className="text-[10px] uppercase tracking-[0.3em] text-emerald-500/70">TRANSMITTER</p>
              <h1 className="font-display text-xl text-white">Node Setup</h1>
            </div>
          </div>
          <Link href="/monitor" className="text-xs uppercase tracking-widest text-fog/50 hover:text-white">
            Mon
          </Link>
        </header>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="space-y-4">
             <label className="block">
               <span className="text-[10px] uppercase tracking-widest text-fog/50 mb-1 block">Node ID (Persistent)</span>
               <input disabled value={nodeId} className="w-full bg-black border border-white/10 px-3 py-2 text-xs font-mono text-fog/50 uppercase" />
             </label>
             <label className="block">
               <span className="text-[10px] uppercase tracking-widest text-fog/50 mb-1 block">Designation</span>
               <input disabled={status !== 'idle'} value={cameraName} onChange={e => setCameraName(e.target.value)} className="w-full bg-[#121212] border border-white/20 px-3 py-2 text-sm font-mono text-white focus:border-emerald-500 outline-none transition-colors" />
             </label>
             <label className="block">
               <span className="text-[10px] uppercase tracking-widest text-fog/50 mb-1 block">Sector / Location</span>
               <input disabled={status !== 'idle'} value={location} onChange={e => setLocation(e.target.value)} className="w-full bg-[#121212] border border-white/20 px-3 py-2 text-sm font-mono text-white focus:border-emerald-500 outline-none transition-colors" />
             </label>
          </div>

          <div className="pt-4 border-t border-white/10">
             {status === 'idle' || status === 'error' ? (
                <button 
                  onClick={handleActivate}
                  className="w-full bg-emerald-500 hover:bg-emerald-400 text-black font-bold uppercase tracking-widest py-3 text-xs transition-colors"
                >
                  {status === 'error' ? 'RETRY CONNECTION' : 'ACTIVATE NODE & CONNECT'}
                </button>
             ) : status === 'connecting' ? (
                <button disabled className="w-full border border-emerald-500/50 text-emerald-500 font-bold uppercase tracking-widest py-3 text-xs flex items-center justify-center gap-2">
                  <span className="h-2 w-2 bg-emerald-500 rounded-full animate-pulse"></span>
                  ESTABLISHING LINK...
                </button>
             ) : (
                <button 
                  onClick={handleDeactivate}
                  className="w-full border border-red-500/50 hover:bg-red-500/10 text-red-500 font-bold uppercase tracking-widest py-3 text-xs transition-colors"
                >
                  SEVER CONNECTION
                </button>
             )}
             
             {error && <p className="mt-4 text-[10px] font-mono text-red-400 uppercase">{error}</p>}
          </div>
        </div>
      </aside>

      {/* Main Video Area */}
      <section className="flex-1 relative bg-black flex flex-col items-center justify-center overflow-hidden">
         <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.8)_100%)] z-10" />
         
         {status === 'idle' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center z-20 text-fog/30 font-mono text-sm uppercase tracking-widest">
               <span className="mb-2 text-4xl">NO SIGNAL</span>
               <span>Awaiting Activation</span>
            </div>
         )}
         
         <div className={`relative w-full h-full transition-opacity duration-1000 ${status === 'active' ? 'opacity-100' : 'opacity-0'}`}>
            <video
              ref={videoRef}
              className="absolute inset-0 w-full h-full object-cover grayscale-[20%] contrast-125"
              autoPlay
              muted
              playsInline
            />
            
            {/* CCTV Overlays */}
            <div className="absolute inset-0 pointer-events-none z-20">
               {/* Center Crosshairs */}
               <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center justify-center opacity-40">
                  <div className="absolute h-20 w-[1px] bg-white/60"></div>
                  <div className="absolute h-[1px] w-20 bg-white/60"></div>
                  <div className="h-8 w-8 rounded-full border border-white/60"></div>
               </div>

               {/* Top Overlay */}
               <div className="absolute left-6 top-6 right-6 flex items-start justify-between drop-shadow-md">
                  <div className="flex flex-col">
                     <span className="font-mono text-sm font-bold tracking-widest text-white">
                        {cameraName.toUpperCase()} / {location.toUpperCase()}
                     </span>
                     <span className="font-mono text-xs text-emerald-400">
                        TX_NODE: {nodeId}
                     </span>
                  </div>
                  
                  <div className="flex flex-col items-end">
                     <span className="font-mono text-sm font-bold text-white">
                        {timeStr}
                     </span>
                     <div className="flex items-center gap-2 mt-1 bg-black/50 px-2 py-0.5 border border-emerald-500/30">
                        <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,1)]" />
                        <span className="font-mono text-[10px] font-bold tracking-widest text-emerald-500">LIVE UPLINK</span>
                     </div>
                  </div>
               </div>
            </div>
         </div>
      </section>
    </main>
  );
}
