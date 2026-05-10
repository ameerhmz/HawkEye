import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import requests
from dotenv import load_dotenv
from livekit import api, rtc
from ultralytics import YOLO

from app.behavior_detector import get_behavior_detector

try:
    import torch
except Exception:  # pragma: no cover - optional GPU dependency
    torch = None

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("worker")

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ----------------- Configuration -----------------
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "hawkeye_dev_key")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "hawkeye_dev_secret_2026_xxxxxxxxxxxxxxxx")
ROOM_NAME = os.getenv("LIVEKIT_ROOM", "hawkeye")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Model Settings
MODEL_PATH = os.getenv("MODEL_PATH", "yolov10n.pt")
TARGET_FPS = float(os.getenv("TARGET_FPS", "10"))
FRAME_INTERVAL = 1.0 / TARGET_FPS if TARGET_FPS > 0 else 0.1
YOLO_IMGSZ = int(os.getenv("YOLO_IMGSZ", "416"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.45"))
IOU_MATCH_THRESHOLD = float(os.getenv("IOU_MATCH_THRESHOLD", "0.3"))
MIN_BOX_AREA = float(os.getenv("MIN_BOX_AREA", "0.01"))
MAX_INFERENCE_CONCURRENCY = int(os.getenv("MAX_INFERENCE_CONCURRENCY", "1"))
INTRUSION_DWELL_SECS = float(os.getenv("INTRUSION_DWELL_SECS", "1.0"))
ZONES_DIR = os.path.join(ROOT_DIR, "backend", "static", "zones")

# Behavior Anomaly Detection
ENABLE_BEHAVIOR_DETECTION = os.getenv("ENABLE_BEHAVIOR_DETECTION", "true").lower() == "true"
ANOMALY_ALERT_COOLDOWN = float(os.getenv("ANOMALY_ALERT_COOLDOWN", "10"))

if os.getenv("YOLO_DEVICE"):
    YOLO_DEVICE = os.getenv("YOLO_DEVICE")
elif torch is not None and torch.cuda.is_available():
    YOLO_DEVICE = 0
else:
    YOLO_DEVICE = "cpu"

# Danger Zone: (x1_pct, y1_pct, x2_pct, y2_pct)
# Default: right 30% of the frame
DANGER_ZONE = (0.70, 0.0, 1.0, 1.0)

# Alert Thresholds
LOITERING_THRESHOLD_SECS = float(os.getenv("LOITERING_THRESHOLD_SECS", "15"))
RUNNING_VELOCITY_THRESHOLD = float(os.getenv("RUNNING_VELOCITY_THRESHOLD", "200"))
FALLING_ASPECT_RATIO_THRESHOLD = float(os.getenv("FALLING_ASPECT_RATIO_THRESHOLD", "1.2"))
STALE_TRACK_SECS = float(os.getenv("STALE_TRACK_SECS", "8"))

ALERT_COOLDOWNS = {
    "object_detection": float(os.getenv("COOLDOWN_DETECTION", "30")),
    "intrusion": float(os.getenv("COOLDOWN_INTRUSION", "10")),
    "loitering": float(os.getenv("COOLDOWN_LOITERING", "30")),
    "running": float(os.getenv("COOLDOWN_RUNNING", "10")),
    "falling": float(os.getenv("COOLDOWN_FALLING", "20")),
    "behavior_anomaly": float(os.getenv("COOLDOWN_ANOMALY", "10"))
}

SNAPSHOT_DIR = os.path.join(ROOT_DIR, "backend", "static", "snapshots")

logger.info(f"Loading {MODEL_PATH} model...")
try:
    model = YOLO(MODEL_PATH)
except Exception as model_error:
    fallback_model = "yolov8n.pt"
    logger.warning(f"Failed to load {MODEL_PATH}: {model_error}. Falling back to {fallback_model}.")
    model = YOLO(fallback_model)
    MODEL_PATH = fallback_model
logger.info("Model loaded.")
inference_semaphore = asyncio.Semaphore(max(1, MAX_INFERENCE_CONCURRENCY))


def predict_frame(image: np.ndarray):
    if torch is not None:
        with torch.inference_mode():
            return model.predict(
                image,
                conf=CONFIDENCE_THRESHOLD,
                imgsz=YOLO_IMGSZ,
                device=YOLO_DEVICE,
                verbose=False,
            )
    return model.predict(
        image,
        conf=CONFIDENCE_THRESHOLD,
        imgsz=YOLO_IMGSZ,
        device=YOLO_DEVICE,
        verbose=False,
    )

# ----------------- Data Structures -----------------

@dataclass
class TrackState:
    track_id: int
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    bbox_history: List[Tuple[float, float, float, float, float, float, float]] = field(
        default_factory=list
    )
    last_alert_at: Dict[str, float] = field(default_factory=dict)
    in_zone: bool = False
    zone_enter_at: Optional[float] = None

    @property
    def dwell_time(self) -> float:
        return self.last_seen - self.first_seen

    @property
    def latest_bbox(self) -> Optional[Tuple[float, float, float, float, float, float, float]]:
        return self.bbox_history[-1] if self.bbox_history else None

    @property
    def prev_bbox(self) -> Optional[Tuple[float, float, float, float, float, float, float]]:
        return self.bbox_history[-2] if len(self.bbox_history) >= 2 else None


@dataclass
class CameraState:
    camera_name: str
    camera_id: int
    next_track_id: int = 1
    tracks: Dict[int, TrackState] = field(default_factory=dict)
    zone_polygon: Optional[List[Tuple[float, float]]] = None
    behavior_detector: Optional[object] = None  # BehaviorAnomalyDetector instance
    anomaly_detector_frame_count: int = 0
    last_anomaly_alert_at: float = 0.0  # Last time anomaly alert was triggered


camera_states: Dict[str, CameraState] = {}
camera_id_cache: Dict[str, Tuple[int, float]] = {}

# ----------------- Helper Functions -----------------

def create_worker_token() -> str:
    token = (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity("ai-worker-01")
        .with_name("AI Vision Worker")
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=ROOM_NAME,
                hidden=True,
                can_publish=True,
                can_subscribe=True,
            )
        )
    )
    return token.to_jwt()

def trigger_alert(
    camera_id: int,
    message: str,
    severity: str,
    alert_type: str,
    track_id: Optional[int] = None,
    dwell_time: Optional[float] = None,
    in_danger_zone: bool = False,
    image_url: Optional[str] = None
):
    try:
        payload = {
            "camera_id": camera_id,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "image_url": image_url,
            "track_id": track_id,
            "dwell_time": dwell_time,
            "in_danger_zone": bool(in_danger_zone)
        }
        
        res = requests.post(f"{API_BASE_URL}/alerts", json=payload, timeout=5)
        if res.ok:
            logger.info(f"Triggered {alert_type} alert: {message}")
        else:
            logger.error(f"Failed to trigger alert: {res.text}")
    except Exception as e:
        logger.error(f"Error sending alert to API: {e}")

def is_in_danger_zone(cx: float, cy: float, w: int, h: int) -> bool:
    zx1 = DANGER_ZONE[0] * w
    zy1 = DANGER_ZONE[1] * h
    zx2 = DANGER_ZONE[2] * w
    zy2 = DANGER_ZONE[3] * h
    return zx1 <= cx <= zx2 and zy1 <= cy <= zy2

def compute_velocity(track: TrackState) -> float:
    if not track.prev_bbox:
        return 0.0
    _, _, _, _, cx1, cy1, t1 = track.prev_bbox
    _, _, _, _, cx2, cy2, t2 = track.latest_bbox
    dt = t2 - t1
    if dt <= 0:
        return 0.0
    dist = np.sqrt((cx2 - cx1) ** 2 + (cy2 - cy1) ** 2)
    return dist / dt

def compute_aspect_ratio(track: TrackState) -> float:
    if not track.latest_bbox:
        return 1.0
    x1, y1, x2, y2, _, _, _ = track.latest_bbox
    w = x2 - x1
    h = y2 - y1
    return w / h if h > 0 else 1.0

def compute_iou(box_a: Tuple[float, float, float, float], box_b: Tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    if union <= 0:
        return 0.0
    return inter_area / union

def is_valid_box(box: Tuple[float, float, float, float], frame_w: int, frame_h: int) -> bool:
    x1, y1, x2, y2 = box
    if x2 <= x1 or y2 <= y1:
        return False
    area = (x2 - x1) * (y2 - y1)
    return area >= (frame_w * frame_h * MIN_BOX_AREA)

def maybe_trigger_alert(track: TrackState, alert_type: str, now: float) -> bool:
    cooldown = ALERT_COOLDOWNS.get(alert_type, 10.0)
    last_at = track.last_alert_at.get(alert_type, 0.0)
    if now - last_at < cooldown:
        return False
    track.last_alert_at[alert_type] = now
    return True

def fetch_camera_id(camera_name: str) -> Optional[int]:
    cached = camera_id_cache.get(camera_name)
    now = time.time()
    if cached and now - cached[1] < 60:
        return cached[0]

    try:
        res = requests.get(f"{API_BASE_URL}/camera/list", timeout=5)
        if not res.ok:
            logger.error(f"Camera list fetch failed: {res.text}")
            return None
        cameras = res.json()
        for cam in cameras:
            if cam.get("name") == camera_name:
                camera_id_cache[camera_name] = (cam.get("id"), now)
                return cam.get("id")
    except Exception as e:
        logger.error(f"Error fetching cameras: {e}")
    return None


def load_zone_for_camera(identity: str, display_name: Optional[str]) -> Optional[List[Tuple[float, float]]]:
    """Load a normalized polygon for the camera from `backend/static/zones/<id>.json` or `<name>.json`.
    File format: { "polygon": [[x1,y1], [x2,y2], ...] } with coordinates in 0..1 (normalized).
    """
    try:
        candidates = []
        if identity:
            candidates.append(os.path.join(ZONES_DIR, f"{identity}.json"))
        if display_name:
            safe = display_name.replace(" ", "_")
            candidates.append(os.path.join(ZONES_DIR, f"{safe}.json"))

        for path in candidates:
            if os.path.exists(path):
                with open(path, "r") as fh:
                    data = json.load(fh)
                    poly = data.get("polygon") or data.get("zone")
                    if poly and isinstance(poly, list):
                        return [(float(x), float(y)) for x, y in poly]
    except Exception as e:
        logger.warning(f"Failed to load zone for {identity}/{display_name}: {e}")
    return None


def point_in_polygon(x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
    # Ray casting algorithm for point-in-polygon
    inside = False
    n = len(polygon)
    if n == 0:
        return False
    px, py = x, y
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        intersect = ((y1 > py) != (y2 > py)) and (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-12) + x1)
        if intersect:
            inside = not inside
    return inside

def save_snapshot(img_bgr: np.ndarray, camera_id: int, track_id: int, now: float) -> Optional[str]:
    try:
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        filename = f"snapshot_{camera_id}_{track_id}_{int(now)}.jpg"
        file_path = os.path.join(SNAPSHOT_DIR, filename)
        cv2.imwrite(file_path, img_bgr)
        return f"/static/snapshots/{filename}"
    except Exception as e:
        logger.error(f"Snapshot save failed: {e}")
        return None

# ----------------- Video Processing -----------------

async def process_track(track: rtc.RemoteVideoTrack, room: rtc.Room, participant_identity: str, participant_name: Optional[str] = None):
    logger.info(f"Starting processing for track {track.sid}")
    stream = rtc.VideoStream(track)

    # Use participant identity as the unique key (participant.identity is unique per client)
    key = participant_identity

    # Try to resolve camera id by identity first, then fallback to display name
    camera_id = fetch_camera_id(participant_identity) or (fetch_camera_id(participant_name) if participant_name else None) or 1
    camera_state = camera_states.get(key)
    if not camera_state:
        camera_state = CameraState(camera_name=participant_name or participant_identity, camera_id=camera_id)
        # Initialize behavior anomaly detector if enabled
        if ENABLE_BEHAVIOR_DETECTION:
            try:
                behavior_detector = get_behavior_detector()
                camera_state.behavior_detector = behavior_detector
                logger.info(f"Initialized behavior anomaly detector for {camera_state.camera_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize behavior detector: {e}")
        camera_states[key] = camera_state
    else:
        camera_state.camera_id = camera_id

    frame_count = 0
    last_process_time = 0.0

    try:
        async for frame in stream:
            frame_count += 1
            # Process every 3rd frame to reduce CPU load
            if frame_count % 3 != 0:
                continue

            now = time.time()
            if now - last_process_time < FRAME_INTERVAL:
                continue
            last_process_time = now

            try:
                actual_frame = frame.frame
                rgb_frame = actual_frame.convert(rtc.VideoBufferType.RGB24)
                image_bytes = bytes(rgb_frame.data)
                img = np.frombuffer(image_bytes, dtype=np.uint8).reshape(
                    (rgb_frame.height, rgb_frame.width, 3)
                )
                img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            except Exception as e:
                logger.warning(f"Frame conversion error: {e}")
                continue

            frame_h, frame_w = img_bgr.shape[:2]

            # ===== Behavior Anomaly Detection (Logging Only) =====
            if camera_state.behavior_detector is not None:
                try:
                    # Add frame to behavior detector buffer
                    camera_state.behavior_detector.add_frame(img_bgr)
                    camera_state.anomaly_detector_frame_count += 1
                    
                    # Run anomaly detection every 30 frames (sliding window)
                    if camera_state.anomaly_detector_frame_count % 30 == 0:
                        anomaly_score, is_anomaly = camera_state.behavior_detector.detect_anomaly()
                        
                        if is_anomaly:
                            # Log anomaly detection (no new alert type)
                            now_ts = time.time()
                            cooldown = ALERT_COOLDOWNS.get("behavior_anomaly", 10.0)
                            if now_ts - camera_state.last_anomaly_alert_at >= cooldown:
                                logger.warning(f"Anomaly detected in {camera_state.camera_name}: score={anomaly_score:.2f}")
                                camera_state.last_anomaly_alert_at = now_ts
                except Exception as e:
                    logger.warning(f"Behavior detection error: {e}")
            
            # ===== Object Detection (YOLO) =====
            inference_frame = img_bgr
            max_dim = max(frame_w, frame_h)
            if max_dim > 960:
                scale = 960.0 / max_dim
                inference_frame = cv2.resize(
                    img_bgr,
                    (int(frame_w * scale), int(frame_h * scale)),
                    interpolation=cv2.INTER_LINEAR,
                )

            proc_frame_h, proc_frame_w = inference_frame.shape[:2]

            # Run inference off the event loop so multiple cameras can progress in parallel
            async with inference_semaphore:
                results = await asyncio.to_thread(predict_frame, inference_frame)

            detections = []
            class_map = {int(k): v for k, v in getattr(model, "names", {}).items()} if getattr(model, "names", None) else {}
            if results and results[0].boxes is not None:
                boxes = results[0].boxes
                # iterate by index to access class ids
                for i in range(len(boxes)):
                    try:
                        box = boxes.xyxy[i]
                        conf = float(boxes.conf[i].cpu().numpy().item()) if hasattr(boxes.conf[i], 'cpu') else float(boxes.conf[i])
                        cls = int(boxes.cls[i].cpu().numpy().item()) if hasattr(boxes.cls[i], 'cpu') else int(boxes.cls[i])
                        x1, y1, x2, y2 = box.cpu().numpy().tolist()
                    except Exception:
                        # fallback safe extraction
                        arr = box.cpu().numpy().tolist() if hasattr(box, 'cpu') else list(box)
                        x1, y1, x2, y2 = arr
                        cls = int(boxes.cls[i]) if i < len(boxes.cls) else 0
                        conf = float(boxes.conf[i]) if i < len(boxes.conf) else 0.0

                    bbox = (float(x1), float(y1), float(x2), float(y2))
                    if not is_valid_box(bbox, proc_frame_w, proc_frame_h):
                        continue
                    detections.append({"bbox": bbox, "conf": float(conf), "class_id": cls, "class": class_map.get(cls, str(cls))})

            # Match detections to existing tracks (simple IoU matching)
            assigned = {}
            used_tracks = set()
            for det_idx, det in enumerate(detections):
                best_iou = 0.0
                best_id = None
                for track_id, tstate in camera_state.tracks.items():
                    if track_id in used_tracks or not tstate.latest_bbox:
                        continue
                    prev_box = tstate.latest_bbox[:4]
                    iou = compute_iou(det["bbox"], prev_box)
                    if iou > best_iou:
                        best_iou = iou
                        best_id = track_id
                if best_id is not None and best_iou >= IOU_MATCH_THRESHOLD:
                    assigned[det_idx] = best_id
                    used_tracks.add(best_id)

            # Create tracks for unmatched detections
            for det_idx in range(len(detections)):
                if det_idx in assigned:
                    continue
                new_id = camera_state.next_track_id
                camera_state.next_track_id += 1
                camera_state.tracks[new_id] = TrackState(track_id=new_id)
                assigned[det_idx] = new_id

            boxes_payload = []
            for det_idx, det in enumerate(detections):
                track_id = assigned.get(det_idx)
                if track_id is None:
                    continue

                x1, y1, x2, y2 = det["bbox"]
                w = x2 - x1
                h = y2 - y1
                cx = x1 + (w / 2)
                cy = y1 + (h / 2)

                tstate = camera_state.tracks[track_id]
                is_new_track = len(tstate.bbox_history) == 0
                tstate.last_seen = now
                tstate.bbox_history.append((x1, y1, x2, y2, cx, cy, now))
                if len(tstate.bbox_history) > 30:
                    tstate.bbox_history.pop(0)

                in_zone = is_in_danger_zone(cx, cy, proc_frame_w, proc_frame_h)
                velocity = compute_velocity(tstate)
                aspect_ratio = compute_aspect_ratio(tstate)

                # Simplified: just use class name or "person"
                current_action = det.get("class", "object")

                boxes_payload.append({
                    "class": det.get("class", "obj"),
                    "conf": float(det["conf"]),
                    "x1": float(x1 / proc_frame_w),
                    "y1": float(y1 / proc_frame_h),
                    "x2": float(x2 / proc_frame_w),
                    "y2": float(y2 / proc_frame_h),
                    "track_id": track_id,
                    "action": current_action,
                    "dwell_time": int(tstate.dwell_time)
                })

                # Alerts
                # Trigger initial object detection alerts for any class; person gets higher severity
                det_class = det.get("class", "obj")
                if is_new_track and maybe_trigger_alert(tstate, "object_detection", now):
                    image_url = save_snapshot(img_bgr, camera_id, track_id, now)
                    severity = "low"
                    message = f"{det_class.capitalize()} detected (ID: {track_id})"
                    if det_class == "person":
                        severity = "medium"
                    trigger_alert(
                        camera_id=camera_id,
                        message=message,
                        severity=severity,
                        alert_type="object_detection",
                        track_id=track_id,
                        dwell_time=tstate.dwell_time,
                        in_danger_zone=in_zone,
                        image_url=image_url,
                    )

                # Additional alerts (falling, intrusion, loitering, running) only apply to persons
                if det_class == "person":
                    alert_checks = [
                        ("falling", aspect_ratio > FALLING_ASPECT_RATIO_THRESHOLD, "critical", f"Person {track_id} fell!"),
                        ("intrusion", in_zone, "high", f"Person {track_id} entered Danger Zone!"),
                        (
                            "loitering",
                            tstate.dwell_time >= LOITERING_THRESHOLD_SECS,
                            "high" if in_zone else "medium",
                            f"Person {track_id} loitering for {int(tstate.dwell_time)}s",
                        ),
                        ("running", velocity > RUNNING_VELOCITY_THRESHOLD, "medium", f"Person {track_id} is running!"),
                    ]

                    for alert_type, condition, severity, message in alert_checks:
                        if not condition:
                            continue
                        if not maybe_trigger_alert(tstate, alert_type, now):
                            continue
                        image_url = save_snapshot(img_bgr, camera_id, track_id, now)
                        trigger_alert(
                            camera_id=camera_id,
                            message=message,
                            severity=severity,
                            alert_type=alert_type,
                            track_id=track_id,
                            dwell_time=tstate.dwell_time,
                            in_danger_zone=in_zone,
                            image_url=image_url,
                        )
                        break

            # Prune stale tracks for this camera
            stale_ids = [
                tid for tid, tstate in camera_state.tracks.items() if now - tstate.last_seen > STALE_TRACK_SECS
            ]
            for tid in stale_ids:
                del camera_state.tracks[tid]

            payload = {
                "track_sid": track.sid,
                "camera_identity": participant_identity,
                "camera_name": participant_name,
                "boxes": boxes_payload
            }
            try:
                await room.local_participant.publish_data(
                    payload=json.dumps(payload).encode("utf-8"),
                    topic="bounding_boxes"
                )
            except Exception as e:
                logger.warning(f"Failed publishing data: {e}")

    except Exception as e:
        logger.error(f"Error processing track {track.sid}: {e}")
    finally:
        camera_states.pop(key, None)
        logger.info(f"Stopped processing track {track.sid}")

# ----------------- Main Loop -----------------

async def main():
    logger.info("Initializing LiveKit room...")
    room = rtc.Room()

    @room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        if track.kind == rtc.TrackKind.KIND_VIDEO:
            # Pass both identity (unique) and display name (friendly)
            asyncio.create_task(process_track(track, room, participant.identity, participant.name))

    token = create_worker_token()
    await room.connect(LIVEKIT_URL, token)
    logger.info("Connected to LiveKit room!")

    try:
        while True:
            # Keep loop alive
            await asyncio.sleep(5)
    except KeyboardInterrupt:
        await room.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
