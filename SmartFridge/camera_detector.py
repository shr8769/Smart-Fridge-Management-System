"""
Camera Object Detection for Smart Fridge
Detects items via camera and adds them to the fridge inventory after 7 seconds of consistent detection
"""

import cv2
import numpy as np
import requests
import time
from datetime import datetime

# Configuration
CAMERA_URL = 'http://10.181.154.254:81/stream'  # ESP32-CAM MJPEG stream
BACKEND_URL = 'http://127.0.0.1:3001'
CONFIDENCE_THRESHOLD = 0.5
ADD_DELAY_SECONDS = 7  # Object must be detected for 7 seconds before adding
REMOVE_DELAY_SECONDS = 7  # Object absence for 7 seconds triggers removal
HEARTBEAT_INTERVAL = 1  # Update backend every second

# Whitelist: Only these items will be detected and added to database
ALLOWED_ITEMS = ['orange', 'banana', 'apple', 'carrot']

# Detection state tracker
detection_state = {}
"""
Structure:
{
    "apple": {
        "first_seen": datetime,
        "last_seen": datetime,
        "consecutive_seconds": 6.5,
        "db_added": False,
        "db_id": None,
        "confidence": 0.85
    }
}
"""

# Load COCO class names
classNames = []
classFile = 'Camera/coco.names'
try:
    with open(classFile, 'rt') as f:
        classNames = f.read().rstrip('\n').split('\n')
    print(f"✅ Loaded {len(classNames)} class names from {classFile}")
except FileNotFoundError:
    print(f"❌ Error: {classFile} not found. Please ensure Camera/ folder exists with required files.")
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
        print(f"⚠️  Failed to add {label}: {response.text}")
        return None
    except Exception as e:
        print(f"❌ Error adding {label}: {e}")
        return None


def send_heartbeat(detected_labels):
    """Send heartbeat to backend with currently detected items"""
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
        print(f"⚠️  Heartbeat failed: {e}")
    return 0


def cleanup_stale_items():
    """Trigger backend to remove items not seen for 7+ seconds"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/camera/cleanup",
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            removed = result.get('removed', 0)
            if removed > 0:
                print(f"🗑️  Cleanup removed {removed} stale camera items")
            return removed
    except Exception as e:
        print(f"⚠️  Cleanup failed: {e}")
    return 0


def update_detection_state(detected_items, current_time):
    """Update detection state and handle add/remove logic"""
    global detection_state
    
    detected_labels = set()
    
    # Process currently detected items
    for label, confidence in detected_items:
        # Filter: Only process allowed items
        if label not in ALLOWED_ITEMS:
            continue  # Skip items not in whitelist
        
        detected_labels.add(label)
        
        if label not in detection_state:
            # First time seeing this object
            detection_state[label] = {
                'first_seen': current_time,
                'last_seen': current_time,
                'consecutive_seconds': 0,
                'db_added': False,
                'db_id': None,
                'confidence': confidence
            }
            print(f"👁️  New detection: {label} (confidence: {confidence:.2f}) ✅ ALLOWED")
        else:
            # Update existing detection
            state = detection_state[label]
            state['last_seen'] = current_time
            state['confidence'] = max(state['confidence'], confidence)
            
            # Calculate consecutive detection duration
            time_diff = (current_time - state['first_seen']).total_seconds()
            state['consecutive_seconds'] = time_diff
            
            # Check if we should add to database (7 seconds of continuous detection)
            if not state['db_added'] and time_diff >= ADD_DELAY_SECONDS:
                print(f"⏱️  {label} detected continuously for {time_diff:.1f}s - Adding to database...")
                db_id = add_item_to_backend(label, state['confidence'])
                if db_id:
                    state['db_added'] = True
                    state['db_id'] = db_id
    
    # Check for items that are no longer detected
    all_labels = list(detection_state.keys())
    for label in all_labels:
        if label not in detected_labels:
            # Item not detected in this frame
            state = detection_state[label]
            time_since_last_seen = (current_time - state['last_seen']).total_seconds()
            
            # If item was in database and hasn't been seen for a while, mark for removal
            if state['db_added'] and time_since_last_seen >= REMOVE_DELAY_SECONDS:
                print(f"🗑️  {label} not detected for {time_since_last_seen:.1f}s - Will be removed by cleanup")
                # Remove from our tracking
                del detection_state[label]
            elif time_since_last_seen >= REMOVE_DELAY_SECONDS:
                # Never added to DB, just remove from tracking
                print(f"⏹️  {label} detection ended (never added to DB)")
                del detection_state[label]
    
    return list(detected_labels)


def main():
    """Main camera detection loop"""
    print("=" * 60)
    print("Smart Fridge Camera Detection Started")
    print("=" * 60)
    print(f"📹 Camera URL: {CAMERA_URL}")
    print(f"🔗 Backend URL: {BACKEND_URL}")
    print(f"⏱️  Add delay: {ADD_DELAY_SECONDS}s | Remove delay: {REMOVE_DELAY_SECONDS}s")
    print(f"🎯 Confidence threshold: {CONFIDENCE_THRESHOLD}")
    print(f"✅ Allowed items: {', '.join(ALLOWED_ITEMS)}")
    print(f"🔴 Other items will be shown in RED (filtered)")
    print("=" * 60)
    print("\nPress ESC to stop\n")
    
    # OpenCV VideoCapture for MJPEG stream
    cap = cv2.VideoCapture(CAMERA_URL)
    
    if not cap.isOpened():
        print(f"❌ Error: Cannot open camera stream at {CAMERA_URL}")
        print("   Please check:")
        print("   1. Camera is powered on")
        print("   2. Camera IP address is correct")
        print("   3. Network connection is working")
        return
    
    print("✅ Camera stream opened successfully\n")
    
    winName = 'Smart Fridge Camera'
    cv2.namedWindow(winName, cv2.WINDOW_AUTOSIZE)
    
    last_heartbeat = time.time()
    last_cleanup = time.time()
    frame_count = 0
    
    try:
        while True:
            frame_count += 1
            current_time = datetime.now()
            
            # Capture frame from camera
            ret, img = cap.read()
            if not ret:
                print("⚠️  Failed to grab frame from camera")
                time.sleep(0.1)
                continue
            
            # Detect objects
            classIds, confs, bbox = net.detect(img, confThreshold=CONFIDENCE_THRESHOLD)
            
            # Process detections
            detected_items = []
            filtered_items = []  # Track items that were filtered out
            if len(classIds) != 0:
                for classId, confidence, box in zip(classIds.flatten(), confs.flatten(), bbox):
                    label = classNames[classId - 1]
                    
                    # Check if item is in allowed list
                    if label in ALLOWED_ITEMS:
                        detected_items.append((label, float(confidence)))
                        # Draw GREEN bounding box for allowed items
                        cv2.rectangle(img, box, color=(0, 255, 0), thickness=3)
                        cv2.putText(img, f"{label} {confidence:.2f}", 
                                   (box[0] + 10, box[1] + 30), 
                                   cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)
                    else:
                        filtered_items.append(label)
                        # Draw RED bounding box for filtered items
                        cv2.rectangle(img, box, color=(0, 0, 255), thickness=2)
                        cv2.putText(img, f"{label} (FILTERED)", 
                                   (box[0] + 10, box[1] + 30), 
                                   cv2.FONT_HERSHEY_COMPLEX, 0.8, (0, 0, 255), 2)
            
            # Update detection state
            detected_labels = update_detection_state(detected_items, current_time)
            
            # Send heartbeat every second
            if time.time() - last_heartbeat >= HEARTBEAT_INTERVAL:
                if detected_labels:
                    updated = send_heartbeat(detected_labels)
                last_heartbeat = time.time()
            
            # Run cleanup every 3 seconds
            if time.time() - last_cleanup >= 3:
                cleanup_stale_items()
                last_cleanup = time.time()
            
            # Display status on frame
            status_y = 30
            cv2.putText(img, f"Frame: {frame_count} | Allowed: {len(detected_items)} | Filtered: {len(filtered_items)}", 
                       (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            for label, state in detection_state.items():
                status_y += 30
                status_text = f"{label}: {state['consecutive_seconds']:.1f}s"
                if state['db_added']:
                    status_text += " [IN DB]"
                    color = (0, 255, 0)
                else:
                    color = (0, 255, 255)
                cv2.putText(img, status_text, (10, status_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Show frame
            cv2.imshow(winName, img)
            
            # Check for ESC key
            key = cv2.waitKey(5) & 0xFF
            if key == 27:  # ESC
                print("\n⏹️  Stopping camera detection...")
                break
    
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("✅ Camera detection stopped")


if __name__ == '__main__':
    # Check backend connectivity
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend connection verified\n")
        else:
            print(f"⚠️  Backend returned status {response.status_code}\n")
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("Please ensure backend.py is running!\n")
        exit(1)
    
    main()
