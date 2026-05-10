import os
from datetime import datetime, timezone
from typing import List

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import models, schemas
from .auth import create_access_token, hash_password, verify_password
from .db import SessionLocal, get_db, init_db
from .deps import decode_token, get_optional_user
from .ws_manager import ConnectionManager

AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "false").lower() == "true"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://localhost:3001"
DEFAULT_CORS_ORIGIN_REGEX = (
    r"https?://(localhost|127\.0\.0\.1|10\.87\.3\.189)(:\d+)?"
    r"|https://.*\.ngrok-free\.app"
    r"|https://.*\.trycloudflare\.com"
)


def parse_csv_env(name: str, fallback: str) -> list[str]:
    raw_value = os.getenv(name, fallback)
    return [value.strip() for value in raw_value.split(",") if value.strip()]


cors_allow_origins = parse_csv_env("CORS_ALLOW_ORIGINS", DEFAULT_CORS_ORIGINS)
cors_allow_origin_regex = os.getenv(
    "CORS_ALLOW_ORIGIN_REGEX", DEFAULT_CORS_ORIGIN_REGEX
)

app = FastAPI(title="SAISS Backend", version="0.2.0")
manager = ConnectionManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_origin_regex=cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure snapshots directory exists
backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(backend_root, "static")
os.makedirs(os.path.join(static_dir, "snapshots"), exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def require_user(user=Depends(get_optional_user)):
    if AUTH_REQUIRED and user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


@app.get("/health")
def health_check():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.post("/auth/register", response_model=schemas.UserOut)
def register_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user = models.User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=schemas.Token)
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        subject=user.email,
        expires_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        payload={"role": user.role, "user_id": user.id},
    )
    return schemas.Token(access_token=token)


@app.post("/camera/register", response_model=schemas.CameraOut)
def register_camera(
    payload: schemas.CameraCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_user),
):
    existing = db.query(models.Camera).filter(models.Camera.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Camera name already registered")

    camera = models.Camera(
        name=payload.name,
        location=payload.location,
        stream_url=payload.stream_url,
        status=payload.status,
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


@app.get("/camera/list", response_model=List[schemas.CameraOut])
def list_cameras(db: Session = Depends(get_db), _user=Depends(require_user)):
    return db.query(models.Camera).order_by(models.Camera.id.desc()).all()


@app.post("/events", response_model=schemas.EventOut)
async def create_event(
    payload: schemas.EventCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_user),
):
    event = models.Event(
        camera_id=payload.camera_id,
        event_type=payload.event_type,
        severity=payload.severity,
        confidence=payload.confidence,
        metadata_json=payload.metadata,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    await manager.broadcast(
        {"type": "event", "data": schemas.EventOut.model_validate(event).model_dump()}
    )
    return event


@app.get("/events", response_model=List[schemas.EventOut])
def list_events(db: Session = Depends(get_db), _user=Depends(require_user)):
    return db.query(models.Event).order_by(models.Event.id.desc()).all()


@app.post("/alerts", response_model=schemas.AlertOut)
async def create_alert(
    payload: schemas.AlertCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_user),
):
    alert = models.Alert(
        camera_id=payload.camera_id,
        alert_type=payload.alert_type,
        severity=payload.severity,
        message=payload.message,
        image_url=payload.image_url,
        track_id=payload.track_id,
        dwell_time=payload.dwell_time,
        in_danger_zone=str(payload.in_danger_zone) if payload.in_danger_zone is not None else None,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    await manager.broadcast(
        {"type": "alert", "data": schemas.AlertOut.model_validate(alert).model_dump()}
    )
    return alert


@app.get("/alerts", response_model=List[schemas.AlertOut])
def list_alerts(db: Session = Depends(get_db), _user=Depends(require_user)):
    return db.query(models.Alert).order_by(models.Alert.id.desc()).all()


@app.get("/recordings", response_model=List[schemas.RecordingOut])
def list_recordings(db: Session = Depends(get_db), _user=Depends(require_user)):
    return db.query(models.Recording).order_by(models.Recording.id.desc()).all()


@app.websocket("/ws/alerts")
async def alerts_socket(websocket: WebSocket):
    if AUTH_REQUIRED:
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008)
            return
        try:
            payload = decode_token(token)
        except HTTPException:
            await websocket.close(code=1008)
            return
        db = SessionLocal()
        try:
            user = (
                db.query(models.User)
                .filter(models.User.email == payload.get("sub"))
                .first()
            )
            if not user:
                await websocket.close(code=1008)
                return
        finally:
            db.close()

    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
