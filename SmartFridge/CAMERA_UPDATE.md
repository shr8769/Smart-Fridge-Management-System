# ✅ Camera Code Updated - MJPEG Stream Implementation

## What Changed

Updated `camera_detector.py` to use your **MJPEG stream approach** instead of single image fetching.

### Key Changes:

1. **Camera Connection Method**
   - ❌ Before: `urllib.request.urlopen()` - fetching single JPEG images
   - ✅ Now: `cv2.VideoCapture()` - reading MJPEG video stream
   
2. **Camera URL**
   - ❌ Before: `http://10.181.154.3/cam-hi.jpg`
   - ✅ Now: `http://10.181.154.254:81/stream` (ESP32-CAM MJPEG stream)

3. **Frame Acquisition**
   - ❌ Before: Download → Decode → Rotate each frame
   - ✅ Now: Direct stream reading with `cap.read()`

4. **Performance**
   - ✅ Better: Continuous stream is more efficient
   - ✅ Lower latency between frames
   - ✅ No rotation needed (stream is already oriented correctly)

## Code Comparison

### Old Approach (Single Image Fetch)
```python
imgResponse = urllib.request.urlopen(CAMERA_URL, timeout=5)
imgNp = np.array(bytearray(imgResponse.read()), dtype=np.uint8)
img = cv2.imdecode(imgNp, -1)
img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
```

### New Approach (MJPEG Stream) ✅
```python
cap = cv2.VideoCapture(CAMERA_URL)
ret, img = cap.read()
if not ret:
    print("Failed to grab frame")
    continue
```

## Benefits of MJPEG Stream

1. **Smoother Video** - Continuous stream instead of repeated HTTP requests
2. **Better Performance** - Less overhead, faster frame rate
3. **Error Handling** - VideoCapture has built-in reconnection
4. **Resource Efficient** - Single connection vs multiple HTTP requests

## What Still Works the Same

✅ Object detection logic (7-second add/remove)  
✅ Backend API communication  
✅ Database tracking (source, camera_last_seen)  
✅ All detection state management  
✅ Bounding boxes and labels  
✅ ESC to exit  

## Testing Your Camera

### Step 1: Test Camera Stream Alone

Create a simple test file `test_camera_stream.py`:

```python
import cv2

url = 'http://10.181.154.254:81/stream'
cap = cv2.VideoCapture(url)

if not cap.isOpened():
    print("❌ Cannot open camera stream")
    exit()

print("✅ Camera stream opened!")

while True:
    ret, img = cap.read()
    if not ret:
        print("Failed to grab frame")
        break
    
    cv2.imshow('Test', img)
    
    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()
```

Run:
```powershell
.\fridge\Scripts\python.exe test_camera_stream.py
```

### Step 2: Run Full Detection

Once camera test works:
```powershell
.\fridge\Scripts\python.exe camera_detector.py
```

## Troubleshooting

### Camera won't open
```
❌ Error: Cannot open camera stream
```

**Solutions:**
1. Check ESP32-CAM is powered on
2. Verify IP address: `http://10.181.154.254:81/stream`
3. Test in browser - should show video stream
4. Check network connection (same network as camera)
5. Try pinging camera: `ping 10.181.154.254`

### Stream is slow or laggy
- Reduce frame size on ESP32-CAM settings
- Check WiFi signal strength
- Lower `net.setInputSize()` if needed (currently 320x320)

### Detection not working
- Check model files are in `Camera/` folder
- Verify confidence threshold (default 0.5)
- Ensure objects are well-lit and in frame

## Configuration

Current settings in `camera_detector.py`:

```python
CAMERA_URL = 'http://10.181.154.254:81/stream'  # Your ESP32-CAM stream
BACKEND_URL = 'http://127.0.0.1:3001'
CONFIDENCE_THRESHOLD = 0.5
ADD_DELAY_SECONDS = 7
REMOVE_DELAY_SECONDS = 7
HEARTBEAT_INTERVAL = 1
```

## Required Files Structure

```
SmartFridge/
├── camera_detector.py          ← Updated with MJPEG stream
├── Camera/
│   ├── coco.names
│   ├── ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt
│   └── frozen_inference_graph.pb
├── backend.py
└── fridge/ (venv with opencv-python, numpy)
```

## Next Steps

1. ✅ Camera code updated
2. ✅ Libraries installed (opencv-python, numpy)
3. ⏳ Place model files in `Camera/` folder
4. ⏳ Test camera stream
5. ⏳ Run `camera_detector.py`
6. ⏳ Start detecting items!

---

**Status: Ready for testing with ESP32-CAM! 📹**
