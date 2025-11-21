# Camera Detection System - Quick Start Guide

## 🎯 What Was Implemented

### Phase 1 Complete ✅

1. **Database Schema Updated**
   - Added `source` column (tracks if item is 'manual' or 'camera')
   - Added `camera_last_seen` column (tracks when camera last saw the item)
   - Added index for faster queries

2. **Backend API Enhanced**
   - Modified `/api/items POST` to accept `source` and `confidence` fields
   - Added `/api/camera/heartbeat POST` - Updates last_seen timestamp for detected items
   - Added `/api/camera/cleanup POST` - Removes items not seen for 7+ seconds
   - Added `/api/camera/items GET` - Lists all camera-detected items

3. **Camera Detector Module Created** (`camera_detector.py`)
   - Detects objects using OpenCV and SSD MobileNet
   - **7-second add logic**: Item must be detected continuously for 7 seconds before adding to database
   - **7-second removal logic**: Items not detected for 7 seconds are removed (camera items only)
   - Real-time tracking and visualization
   - Communicates with backend via HTTP API

## 📋 Prerequisites

✅ Backend running on http://127.0.0.1:3001  
✅ MySQL database updated with new columns  
✅ OpenCV installed (`opencv-python`)  
✅ Camera files in `Camera/` folder:
   - `coco.names`
   - `ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt`
   - `frozen_inference_graph.pb`

## 🚀 How to Run

### Step 1: Start the Backend (if not already running)

```powershell
.\fridge\Scripts\python.exe backend.py
```

### Step 2: Update Camera URL (if needed)

Edit `camera_detector.py` line 11:
```python
CAMERA_URL = 'http://10.181.154.254:81/stream'  # ESP32-CAM MJPEG stream URL
```

**Note:** The camera now uses MJPEG stream (VideoCapture) which is better for continuous video than single image fetch.

### Step 3: Start Camera Detection

```powershell
.\fridge\Scripts\python.exe camera_detector.py
```

### Step 4: Test the System

1. **Place an object in front of the camera**
2. **Wait 7 seconds** - You'll see the timer counting up
3. **After 7 seconds** - Item is automatically added to the database with `source='camera'`
4. **Remove the object**
5. **Wait 7 seconds** - Item is automatically removed from the database

## 🎮 Camera Window Controls

- **ESC** - Stop camera detection
- **Status overlay shows**:
  - Frame count and detected objects
  - Each detected item with timer
  - `[IN DB]` indicator when item is added to database

## 🧪 Testing Scenarios

### Test 1: Normal Detection (7-second add)
1. Place an apple in front of camera
2. Watch timer: `apple: 0.0s` → `apple: 7.0s`
3. Check database: `SELECT * FROM item WHERE source='camera';`
4. You should see the apple with `source='camera'`

### Test 2: Quick Movement (should NOT add)
1. Place an item for 3 seconds
2. Remove it
3. Item should NOT be added (didn't reach 7 seconds)

### Test 3: Removal After 7 Seconds
1. Add an item (wait 7 seconds)
2. Remove item from camera view
3. Wait 7 seconds
4. Check database - item should be removed

### Test 4: Manual vs Camera Items
1. Manually add "apple" via UI
2. Camera detects "apple" and adds it after 7 seconds
3. Remove apple from camera
4. After 7 seconds, only the camera-detected apple is removed
5. Manual apple remains in database

## 🔍 Verifying Database Changes

### Check All Items

```sql
SELECT id, label, source, camera_last_seen 
FROM item 
ORDER BY added_date DESC;
```

### Check Only Camera Items

```sql
SELECT * FROM item WHERE source='camera';
```

### Check Manual Items

```sql
SELECT * FROM item WHERE source='manual';
```

## 📊 API Endpoints Added

### 1. Camera Heartbeat
```bash
POST http://127.0.0.1:3001/api/camera/heartbeat
Body: {"labels": ["apple", "banana"]}
```

### 2. Camera Cleanup
```bash
POST http://127.0.0.1:3001/api/camera/cleanup
```

### 3. Get Camera Items
```bash
GET http://127.0.0.1:3001/api/camera/items
```

### 4. Add Item with Source
```bash
POST http://127.0.0.1:3001/api/items
Body: {
  "label": "apple",
  "quantity": "1 unit",
  "location": "Camera Detected",
  "source": "camera",
  "confidence": 0.85
}
```

## ⚙️ Configuration

Edit `camera_detector.py` to adjust:

```python
CAMERA_URL = 'http://10.181.154.254:81/stream'  # ESP32-CAM MJPEG stream
BACKEND_URL = 'http://127.0.0.1:3001'           # Backend URL
CONFIDENCE_THRESHOLD = 0.5                       # Detection confidence (0-1)
ADD_DELAY_SECONDS = 7                           # Seconds before adding
REMOVE_DELAY_SECONDS = 7                        # Seconds before removing
HEARTBEAT_INTERVAL = 1                          # Update frequency
```

## 🐛 Troubleshooting

### Camera won't connect
```
❌ Cannot connect to backend
```
**Solution**: Make sure `backend.py` is running on port 3001

### Model files not found
```
❌ Error: Camera/coco.names not found
```
**Solution**: Ensure `Camera/` folder exists with all 3 files

### Items not being added
- Check console output for detection logs
- Verify object is detected continuously for 7 seconds
- Check confidence threshold (default 0.5)

### Items not being removed
- Cleanup runs every 3 seconds automatically
- Check `camera_last_seen` timestamp in database
- Ensure 7 seconds have passed since last detection

## 📝 What's Next (Future Phases)

### Phase 2 (Optional Enhancements)
- [ ] UI button to start/stop camera from web interface
- [ ] Show camera status in UI (active/inactive)
- [ ] Visual indicator for camera-detected items vs manual items
- [ ] Adjustable timers from UI
- [ ] Camera feed preview in web interface

### Phase 3 (Advanced Features)
- [ ] Multiple camera support
- [ ] Expiry date prediction for detected items
- [ ] Quantity estimation
- [ ] Item removal tracking (consumed vs removed)

## 🎉 Success Indicators

You'll know it's working when:
- ✅ Camera window shows detected objects with bounding boxes
- ✅ Status overlay shows detection timers
- ✅ Console prints "Added {item} to database" after 7 seconds
- ✅ Items appear in UI with "Camera Detected" location
- ✅ Removed items show "Cleanup removed X stale items" after 7 seconds

---

**Status: Phase 1 Complete and Ready for Testing! 🚀**
