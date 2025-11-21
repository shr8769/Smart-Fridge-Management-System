"""
Camera Stream Server for Smart Fridge
Provides HTTP endpoint for live camera feed with object detection
Can be embedded in web UI
"""

import cv2
import numpy as np
import requests
import time
from datetime import datetime
from flask import Flask, Response, jsonify
import threading
import sys
import io

# Fix Unicode encoding issues on Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Try to import waitress for Windows compatibility
try:
    from waitress import serve
    USE_WAITRESS = True
except ImportError:
    USE_WAITRESS = False
    print("⚠️  Waitress not installed, using Flask's built-in server")

# Configuration
# NOTE: Update this IP address when you switch networks!
# To find your ESP32-CAM IP: Check your router or ESP32-CAM serial monitor
CAMERA_URL = 'http://10.181.154.254:81/stream'  # Change this to match your current network
BACKEND_URL = 'http://127.0.0.1:3001'
CONFIDENCE_THRESHOLD = 0.5
ADD_DELAY_SECONDS = 7
REMOVE_DELAY_SECONDS = 7
HEARTBEAT_INTERVAL = 1
ALLOWED_ITEMS = ['orange', 'banana', 'apple', 'carrot']

# Alternative: Use webcam as fallback (set to 0 for default webcam)
USE_WEBCAM_FALLBACK = False  # Set to True if ESP32-CAM is not available
WEBCAM_INDEX = 0  # Change to 1, 2, etc. if you have multiple cameras

# Detection state tracker
detection_state = {}

# Flask app for streaming
stream_app = Flask(__name__)

# Global variables
camera_cap = None
output_frame = None
lock = threading.Lock()
running = False

# Load COCO class names
classNames = []
classFile = 'Camera/coco.names'
try:
    with open(classFile, 'rt') as f:
        classNames = f.read().rstrip('\n').split('\n')
    print(f"✅ Loaded {len(classNames)} class names")
except FileNotFoundError:
    print(f"❌ Error: {classFile} not found")
    exit(1)

# Load model
configPath = 'Camera/ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt'
weightsPath = 'Camera/frozen_inference_graph.pb'

try:
    net = cv2.dnn_DetectionModel(weightsPath, configPath)
    net.setInputSize(320, 320)
    net.setInputScale(1.0 / 127.5)
    net.setInputMean((127.5, 127.5, 127.5))
    net.setInputSwapRB(True)
    print(f"✅ Model loaded successfully")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    exit(1)


def add_item_to_backend(label, confidence):
    """Add detected item to backend via API"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/items",
            json={
                'label': label,
                'quantity': '1 unit',
                'location': 'Camera Detected',
                'source': 'camera',
                'confidence': confidence
            },
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                item_id = result.get('id')
                print(f"✅ Added {label} to database (ID: {item_id})")
                return item_id
        return None
    except Exception as e:
        print(f"❌ Error adding {label}: {e}")
        return None


def send_heartbeat(detected_labels):
    """Send heartbeat to backend"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/camera/heartbeat",
            json={'labels': detected_labels},
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            return result.get('updated', 0)
    except Exception as e:
        pass
    return 0


def cleanup_stale_items():
    """Trigger backend cleanup"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/camera/cleanup",
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            removed = result.get('removed', 0)
            if removed > 0:
                print(f"🗑️  Cleanup removed {removed} stale items")
            return removed
    except Exception as e:
        pass
    return 0


def update_detection_state(detected_items, current_time):
    """Update detection state and handle add/remove logic"""
    global detection_state
    
    detected_labels = set()
    
    for label, confidence in detected_items:
        if label not in ALLOWED_ITEMS:
            continue
        
        detected_labels.add(label)
        
        if label not in detection_state:
            detection_state[label] = {
                'first_seen': current_time,
                'last_seen': current_time,
                'consecutive_seconds': 0,
                'db_added': False,
                'db_id': None,
                'confidence': confidence
            }
            print(f"👁️  New detection: {label} ({confidence:.2f}) ✅ ALLOWED")
        else:
            state = detection_state[label]
            state['last_seen'] = current_time
            state['confidence'] = max(state['confidence'], confidence)
            
            time_diff = (current_time - state['first_seen']).total_seconds()
            state['consecutive_seconds'] = time_diff
            
            if not state['db_added'] and time_diff >= ADD_DELAY_SECONDS:
                print(f"⏱️  {label} detected for {time_diff:.1f}s - Adding...")
                db_id = add_item_to_backend(label, state['confidence'])
                if db_id:
                    state['db_added'] = True
                    state['db_id'] = db_id
    
    all_labels = list(detection_state.keys())
    for label in all_labels:
        if label not in detected_labels:
            state = detection_state[label]
            time_since_last_seen = (current_time - state['last_seen']).total_seconds()
            
            if state['db_added'] and time_since_last_seen >= REMOVE_DELAY_SECONDS:
                print(f"🗑️  {label} not detected for {time_since_last_seen:.1f}s")
                del detection_state[label]
            elif time_since_last_seen >= REMOVE_DELAY_SECONDS:
                print(f"⏹️  {label} detection ended")
                del detection_state[label]
    
    return list(detected_labels)


def detection_loop():
    """Main detection loop running in background thread"""
    global camera_cap, output_frame, lock, running
    
    print("=" * 60)
    print("🎥 Camera Stream Server Started")
    print("=" * 60)
    
    # Try to connect to camera with fallback options
    if USE_WEBCAM_FALLBACK:
        print(f"📹 Using webcam (index {WEBCAM_INDEX})")
        camera_cap = cv2.VideoCapture(WEBCAM_INDEX)
        camera_source = f"Webcam {WEBCAM_INDEX}"
    else:
        print(f"📹 Attempting to connect to: {CAMERA_URL}")
        print(f"   Please wait, trying to establish connection...")
        
        # Try with different OpenCV backends
        camera_cap = cv2.VideoCapture(CAMERA_URL, cv2.CAP_FFMPEG)
        camera_source = CAMERA_URL
        
        # If FFMPEG fails, try default backend
        if not camera_cap.isOpened():
            print(f"   FFMPEG backend failed, trying default backend...")
            camera_cap = cv2.VideoCapture(CAMERA_URL)
    
    print(f"🔗 Backend URL: {BACKEND_URL}")
    print(f"✅ Allowed items: {', '.join(ALLOWED_ITEMS)}")
    print("=" * 60)
    
    if not camera_cap.isOpened():
        print(f"❌ Error: Cannot open camera stream")
        print(f"   Camera source: {camera_source}")
        print("   ")
        print("   Possible solutions:")
        print("   1. Check if ESP32-CAM web interface is accessible:")
        print(f"      Open in browser: http://10.181.154.254:81")
        print("   2. Verify ESP32-CAM is streaming:")
        print(f"      Test URL: {CAMERA_URL}")
        print("   3. Check if ESP32-CAM firmware is running correctly")
        print("   4. Try restarting ESP32-CAM (power cycle)")
        print("   5. Or set USE_WEBCAM_FALLBACK = True to use PC webcam")
        print("   ")
        running = False
        return
    
    print("✅ Camera stream opened\n")
    
    last_heartbeat = time.time()
    last_cleanup = time.time()
    frame_count = 0
    
    running = True
    
    try:
        while running:
            frame_count += 1
            current_time = datetime.now()
            
            ret, img = camera_cap.read()
            if not ret:
                print("⚠️  Failed to grab frame")
                time.sleep(0.1)
                continue
            
            # Detect objects
            classIds, confs, bbox = net.detect(img, confThreshold=CONFIDENCE_THRESHOLD)
            
            detected_items = []
            filtered_items = []
            
            if len(classIds) != 0:
                for classId, confidence, box in zip(classIds.flatten(), confs.flatten(), bbox):
                    label = classNames[classId - 1]
                    
                    if label in ALLOWED_ITEMS:
                        detected_items.append((label, float(confidence)))
                        cv2.rectangle(img, box, color=(0, 255, 0), thickness=3)
                        cv2.putText(img, f"{label} {confidence:.2f}", 
                                   (box[0] + 10, box[1] + 30), 
                                   cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)
                    else:
                        filtered_items.append(label)
                        cv2.rectangle(img, box, color=(0, 0, 255), thickness=2)
                        cv2.putText(img, f"{label} (FILTERED)", 
                                   (box[0] + 10, box[1] + 30), 
                                   cv2.FONT_HERSHEY_COMPLEX, 0.8, (0, 0, 255), 2)
            
            # Update detection state
            detected_labels = update_detection_state(detected_items, current_time)
            
            # Send heartbeat every second
            if time.time() - last_heartbeat >= HEARTBEAT_INTERVAL:
                if detected_labels:
                    send_heartbeat(detected_labels)
                last_heartbeat = time.time()
            
            # Run cleanup every 3 seconds
            if time.time() - last_cleanup >= 3:
                cleanup_stale_items()
                last_cleanup = time.time()
            
            # Display status on frame
            status_y = 30
            cv2.putText(img, f"Frame: {frame_count} | Allowed: {len(detected_items)} | Filtered: {len(filtered_items)}", 
                       (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            
            for label, state in detection_state.items():
                status_y += 30
                status_text = f"{label}: {state['consecutive_seconds']:.1f}s"
                if state['db_added']:
                    status_text += " [IN DB]"
                    color = (0, 0, 0)  # Black
                else:
                    color = (0, 0, 0)  # Black
                cv2.putText(img, status_text, (10, status_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Update global frame for streaming
            with lock:
                output_frame = img.copy()
    
    except Exception as e:
        print(f"❌ Detection loop error: {e}")
    
    finally:
        if camera_cap:
            camera_cap.release()
        running = False
        print("✅ Camera detection stopped")


def generate_frames():
    """Generator function to stream frames as MJPEG"""
    global output_frame, lock
    
    while True:
        with lock:
            if output_frame is None:
                continue
            
            # Encode frame as JPEG
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame)
            
            if not flag:
                continue
        
        # Yield frame in byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
              bytearray(encodedImage) + b'\r\n')


@stream_app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@stream_app.route('/health')
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'running': running, 'camera_opened': camera_cap is not None and camera_cap.isOpened()})


@stream_app.route('/')
def index():
    """Index page"""
    return jsonify({
        'message': 'Camera Stream Server Running',
        'endpoints': {
            '/video_feed': 'MJPEG video stream',
            '/health': 'Health check',
        },
        'status': 'running' if running else 'stopped'
    })


def start_stream_server():
    """Start the detection loop and stream server"""
    # Start detection in background thread
    detection_thread = threading.Thread(target=detection_loop, daemon=True)
    detection_thread.start()
    
    # Start server (use Waitress on Windows for better subprocess compatibility)
    print("\n🌐 Stream server starting on http://0.0.0.0:5001")
    if USE_WAITRESS and sys.platform == 'win32':
        print("   Using Waitress server (Windows-optimized)")
        serve(stream_app, host='0.0.0.0', port=5001, threads=4)
    else:
        print("   Using Flask built-in server")
        stream_app.run(host='0.0.0.0', port=5001, threaded=True, debug=False, use_reloader=False)


if __name__ == '__main__':
    start_stream_server()
