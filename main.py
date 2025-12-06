# main.py
from fastapi import FastAPI, UploadFile, File, Form
from hashlib import sha256
from uuid import uuid4
from datetime import datetime
import os
import sqlite3
import jwt  # PyJWT

app = FastAPI()
SECRET_KEY = "certivo-secret-key"
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- SQLite setup ---
conn = sqlite3.connect("certivo.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS devices (
                token_id TEXT PRIMARY KEY,
                device_id TEXT,
                verification_timestamp TEXT
            )''')
conn.commit()

# --- POST /v1/verify ---
@app.post("/v1/verify")
def verify(video: UploadFile = File(...), audio: UploadFile = File(...), device_id: str = Form(...)):
    # Save uploaded files temporarily
    video_path = f"{UPLOAD_DIR}/{uuid4()}_{video.filename}"
    with open(video_path, "wb") as f:
        f.write(video.file.read())
    audio_path = f"{UPLOAD_DIR}/{uuid4()}_{audio.filename}"
    with open(audio_path, "wb") as f:
        f.write(audio.file.read())
    
    # --- Simulated Human Verification ---
    liveness_score = 0.95      # dummy score for prototype
    lip_sync_score = 0.92      # dummy score
    challenge_passed = True
    replay_flag = False
    
    # --- Simulated DeviceTrust Module ---
    device_trust_score = 0.97  # assume device safe
    
    # --- Fusion Engine ---
    verified = (liveness_score >= 0.8 and
                lip_sync_score >= 0.8 and
                challenge_passed and
                not replay_flag and
                device_trust_score >= 0.75)
    
    # --- Trusted Device Token ---
    if verified:
        device_signature = sha256(device_id.encode()).hexdigest()
        token_payload = {
            "token_id": str(uuid4()),
            "device_id": device_id,
            "device_signature": device_signature,
            "verified": True,
            "timestamp_utc": datetime.utcnow().isoformat()
        }
        trusted_device_token = jwt.encode(token_payload, SECRET_KEY, algorithm="HS256")
        
        # Store token in DB
        c.execute("INSERT INTO devices VALUES (?, ?, ?)", 
                  (token_payload["token_id"], device_id, token_payload["timestamp_utc"]))
        conn.commit()
    else:
        trusted_device_token = None
    
    return {
        "verified": verified,
        "liveness_score": liveness_score,
        "lip_sync_score": lip_sync_score,
        "challenge_passed": challenge_passed,
        "replay_flag": replay_flag,
        "device_trust_score": device_trust_score,
        "trusted_device_token": trusted_device_token,
        "details": {
            "reasons": ["liveness_ok", "challenge_ok", "lip_sync_ok", "device_safe"],
            "timestamp_utc": datetime.utcnow().isoformat()
        }
    }

# --- GET /v1/device-token/{token} ---
@app.get("/v1/device-token/{token}")
def validate_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return {"valid": True, "payload": payload}
    except jwt.ExpiredSignatureError:
        return {"valid": False, "reason": "Token expired"}
    except jwt.InvalidTokenError:
        return {"valid": False, "reason": "Invalid token"}

# --- Optional Admin Endpoint: Revoke Device ---
@app.post("/v1/revoke-device")
def revoke_device(token: str = Form(...)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        token_id = payload.get("token_id")
        c.execute("DELETE FROM devices WHERE token_id=?", (token_id,))
        conn.commit()
        return {"revoked": True, "token_id": token_id}
    except Exception as e:
        return {"revoked": False, "error": str(e)}
