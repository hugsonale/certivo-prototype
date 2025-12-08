# real_human_verification.py
import cv2
import mediapipe as mp
import numpy as np
from moviepy.editor import VideoFileClip
from scipy.spatial import distance as dist

mp_face = mp.solutions.face_detection
mp_mesh = mp.solutions.face_mesh

# ----------------------------------------------------------
# Helper: Calculate Eye Aspect Ratio (blink detection)
# ----------------------------------------------------------
def eye_aspect_ratio(landmarks, eye_points):
    p = np.array([(landmarks[i].x, landmarks[i].y) for i in eye_points])
    A = dist.euclidean(p[1], p[5])
    B = dist.euclidean(p[2], p[4])
    C = dist.euclidean(p[0], p[3])
    ear = (A + B) / (2.0 * C)
    return ear

# ----------------------------------------------------------
# Extract mouth-open ratio (for lip movement detection)
# ----------------------------------------------------------
def mouth_open_ratio(landmarks):
    top = landmarks[13]
    bottom = landmarks[14]
    return abs(bottom.y - top.y)

# ----------------------------------------------------------
# MAIN FUNCTION: Human Verification
# ----------------------------------------------------------
def run_real_human_verification(video_path):
    cap = cv2.VideoCapture(video_path)

    face_detected = False
    blink_count = 0
    frame_count = 0
    mouth_movements = []
    head_movement = []
    
    with mp_mesh.FaceMesh(static_image_mode=False) as face_mesh:
        prev_nose = None

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_count += 1

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = face_mesh.process(rgb)

            if not result.multi_face_landmarks:
                continue

            face_detected = True
            landmarks = result.multi_face_landmarks[0].landmark

            # ---- EAR for blink detection ----
            left_eye = [33, 160, 158, 133, 153, 144]
            right_eye = [362, 385, 387, 263, 373, 380]

            leftEAR = eye_aspect_ratio(landmarks, left_eye)
            rightEAR = eye_aspect_ratio(landmarks, right_eye)

            if (leftEAR + rightEAR) / 2 < 0.19:
                blink_count += 1

            # ---- Mouth movement ----
            mouth_ratio = mouth_open_ratio(landmarks)
            mouth_movements.append(mouth_ratio)

            # ---- Head movement (nose position) ----
            nose = landmarks[1]
            if prev_nose:
                movement = abs(nose.x - prev_nose.x) + abs(nose.y - prev_nose.y)
                head_movement.append(movement)
            prev_nose = nose

    cap.release()

    # -----------------------------------------------------
    # Replay Attack Detection
    # -----------------------------------------------------
    replay_flag = (blink_count == 0 or np.mean(head_movement) < 0.001)

    # -----------------------------------------------------
    # Liveness Score
    # -----------------------------------------------------
    liveness_score = min(1.0, blink_count * 0.2 + np.mean(head_movement) * 50)

    # -----------------------------------------------------
    # Lip-Sync Score
    # -----------------------------------------------------
    audio_clip = VideoFileClip(video_path).audio
    audio_array = audio_clip.to_soundarray(fps=16000)
    audio_energy = np.mean(np.abs(audio_array))

    mouth_energy = np.mean(mouth_movements)

    if audio_energy == 0:
        lip_sync_score = 0
    else:
        lip_sync_score = min(1.0, (mouth_energy * 30) / (audio_energy * 10))

    # -----------------------------------------------------
    # Challenge Passed
    # -----------------------------------------------------
    challenge_passed = (
        face_detected and
        blink_count > 0 and
        lip_sync_score > 0.3 and
        liveness_score > 0.4 and
        not replay_flag
    )

    return {
        "liveness_score": round(liveness_score, 2),
        "lip_sync_score": round(lip_sync_score, 2),
        "challenge_passed": challenge_passed,
        "replay_flag": replay_flag,
        "message": "Real verification complete"
    }
