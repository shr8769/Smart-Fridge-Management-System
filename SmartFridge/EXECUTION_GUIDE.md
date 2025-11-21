# 🚀 SmartFridge - Complete Execution Guide

## 📋 Step-by-Step Execution Order

### ⚠️ IMPORTANT: One-Time Setup (Already Done!)

The database migration has **already been executed successfully**. You don't need to run it again unless you reset your database.

If you need to run it again:
```powershell
.\fridge\Scripts\python.exe migrate_db.py
```
✅ **Status: Migration completed - tables updated**

---

## 🎯 How to Run Your SmartFridge Application

### Step 1: Start the Backend Server (REQUIRED - Always First!)
```powershell
.\fridge\Scripts\python.exe backend.py
```

**What it does:**
- Starts Flask web server on port 3001
- Serves your web UI (index.html)
- Handles database operations (add/delete/view items)
- Provides API endpoints for camera detection
- Processes recipe generation requests
- Handles voice queries

**When to use:**
- **ALWAYS run this first before anything else**
- Keep this terminal window open while using the app
- Stop with `Ctrl+C` when done

**Expected output:**
```
 * Running on http://127.0.0.1:3001
 * Running on http://10.181.154.3:3001
Press CTRL+C to quit
 * Restarting with stat
 * Debugger is active!
```

**Access your app:**
- Open browser: `http://127.0.0.1:3001`
- Or: `http://localhost:3001`

---

### Step 2: Use the Web Interface

Once backend is running:
1. Open browser: `http://127.0.0.1:3001`
2. Add items manually
3. Generate recipes
4. Use voice queries
5. View your fridge inventory

**This is the main way to interact with your app!**

---

### Step 3: Start Camera Detection (OPTIONAL - Only if using camera)

**Before running, ensure:**
- ✅ Backend is running (Step 1)
- ✅ Model files are in `Camera/` folder
- ✅ ESP32-CAM is powered on and connected

```powershell
.\fridge\Scripts\python.exe camera_detector.py
```

**What it does:**
- Opens camera feed window
- Detects objects in real-time
- Automatically adds items after 7 seconds
- Automatically removes items after 7 seconds absence
- Communicates with backend API

**When to use:**
- Only when you want automatic item detection
- Can run without this if you prefer manual entry only
- Stop with `Ctrl+C` or close the window

**Expected output:**
```
Loading model... Done
Starting camera stream...
Camera opened successfully
Starting detection loop...
Detected: apple (confidence: 0.87) - 1s
Detected: apple (confidence: 0.89) - 2s
...
Detected: apple (confidence: 0.91) - 7s
✅ Added apple to database
```

---

### Step 4: Testing & Verification (OPTIONAL)

These are **test scripts** - not required for normal operation:

#### Test 1: Camera Stream Test
```powershell
.\fridge\Scripts\python.exe test_camera_stream.py
```
- Tests if camera connection works
- Shows live video feed
- Press ESC to close
- **Use this to verify camera before running full detection**

#### Test 2: System Readiness Check
```powershell
.\fridge\Scripts\python.exe test_camera_ready.py
```
- Checks if all requirements are met
- Verifies model files exist
- Tests backend connection
- Tests database connection
- **Use this to diagnose issues**

---

## 📁 Complete File Directory - What Each File Does

### 🔵 Core Application Files (Main Components)

#### `backend.py` ⭐ **MOST IMPORTANT**
**Purpose:** Main Flask web server - the heart of your application

**What it does:**
- Serves the web interface (index.html)
- Connects to MySQL database
- Handles all API requests:
  - `/api/items` - Add/view/delete items
  - `/api/generate-recipes` - Generate recipes with Gemini AI
  - `/api/voice-query` - Process voice questions
  - `/api/camera/heartbeat` - Update camera item timestamps
  - `/api/camera/cleanup` - Remove stale camera items
  - `/api/camera/items` - List camera-detected items
- Manages database CRUD operations

**When to run:** Always! This must be running for anything to work.

**How to run:**
```powershell
.\fridge\Scripts\python.exe backend.py
```

---

#### `camera_detector.py` ⭐ **CAMERA MODULE**
**Purpose:** Real-time object detection with smart add/remove logic

**What it does:**
- Connects to ESP32-CAM MJPEG stream
- Uses OpenCV DNN with SSD MobileNet model
- Detects objects (food items) in camera view
- Tracks detection time for each item
- **Adds to database** after 7 seconds continuous detection
- **Removes from database** after 7 seconds absence
- Shows live video with bounding boxes and timers
- Sends heartbeat to backend to keep items "alive"

**When to run:** Only when you want automatic camera-based detection

**How to run:**
```powershell
.\fridge\Scripts\python.exe camera_detector.py
```

**Dependencies:**
- Requires `backend.py` running first
- Requires model files in `Camera/` folder
- Requires ESP32-CAM powered on

---

### 🟢 Database Setup Files (One-Time Use)

#### `add_camera_columns.sql` 📄 **SQL MIGRATION**
**Purpose:** SQL script to add camera tracking columns to database

**What it does:**
```sql
ALTER TABLE item ADD COLUMN source VARCHAR(20) DEFAULT 'manual';
ALTER TABLE item ADD COLUMN camera_last_seen DATETIME NULL;
```
- Adds `source` column (tracks if item is 'manual' or 'camera')
- Adds `camera_last_seen` column (timestamp for cleanup)
- Adds index for performance

**When to run:** 
- ❌ **DON'T RUN THIS DIRECTLY** - Use `migrate_db.py` instead
- Only needed once (already executed)

**How to run (if needed manually):**
```sql
-- In MySQL Workbench or command line
USE smartfridge;
SOURCE add_camera_columns.sql;
```

---

#### `migrate_db.py` ⭐ **PYTHON MIGRATION**
**Purpose:** Automated database migration script

**What it does:**
- Connects to your MySQL database
- Checks if columns already exist (prevents errors)
- Adds `source` and `camera_last_seen` columns
- Creates index for optimization
- Provides success/error feedback

**When to run:** 
- ✅ **Already executed successfully!**
- Only run again if you reset your database

**How to run:**
```powershell
.\fridge\Scripts\python.exe migrate_db.py
```

**Expected output:**
```
Migration completed successfully!
Added columns: source, camera_last_seen
```

---

### 🟡 Testing & Verification Files

#### `test_camera_stream.py` 🧪 **CAMERA TEST**
**Purpose:** Simple camera connection test

**What it does:**
- Opens ESP32-CAM stream
- Displays live video feed
- No detection, no database interaction
- Just verifies camera works
- Press ESC to close

**When to run:** 
- Before running full camera detection
- To troubleshoot camera connection issues
- To verify ESP32-CAM is accessible

**How to run:**
```powershell
.\fridge\Scripts\python.exe test_camera_stream.py
```

---

#### `test_camera_ready.py` 🧪 **READINESS CHECK**
**Purpose:** System diagnostics and verification

**What it does:**
- ✅ Checks if model files exist in `Camera/` folder
- ✅ Tests backend API connection
- ✅ Tests database connection
- ✅ Verifies Python packages installed
- Provides detailed status report

**When to run:**
- Before running camera detection for the first time
- When troubleshooting issues
- To verify setup is complete

**How to run:**
```powershell
.\fridge\Scripts\python.exe test_camera_ready.py
```

**Expected output:**
```
✅ Model files: Found
✅ Backend API: Running
✅ Database: Connected
✅ Required packages: Installed
System is ready!
```

---

### 📘 Documentation Files (Read-Only)

#### `CAMERA_SETUP.md` 📖
**Purpose:** Comprehensive camera setup guide

**Contains:**
- Model file download links
- Camera configuration steps
- Troubleshooting tips
- Testing procedures
- API endpoint documentation

**When to use:** Reference when setting up camera detection

---

#### `CAMERA_UPDATE.md` 📖
**Purpose:** MJPEG implementation details

**Contains:**
- Explanation of MJPEG vs URL fetch
- Code changes made
- Performance benefits
- Technical details

**When to use:** Understanding how camera code works

---

#### `IMPLEMENTATION_SUMMARY.md` 📖
**Purpose:** Complete project overview

**Contains:**
- All features implemented
- Testing checklist
- Configuration details
- Database queries
- Troubleshooting guide
- Flow diagrams

**When to use:** Reference for understanding entire system

---

#### `EXECUTION_GUIDE.md` 📖 **(This File!)**
**Purpose:** Step-by-step execution instructions

**Contains:**
- How to run each file
- Execution order
- File purposes
- Expected outputs

**When to use:** When you need to run the application

---

### 🟣 Configuration Files

#### `requirements.txt` 📦
**Purpose:** Python package dependencies list

**Contains:**
```
Flask==3.1.2
flask-cors==5.0.0
PyMySQL==1.1.2
python-dotenv==1.0.1
requests==2.32.3
google-generativeai==0.8.3
SpeechRecognition==3.12.0
gTTS==2.5.4
opencv-python==4.12.0.88
numpy==2.2.6
```

**When to use:**
- Installing packages: `pip install -r requirements.txt`
- Already installed in your `fridge` virtualenv

---

### 🟠 Frontend Files

#### `folder/index.html` 🌐
**Purpose:** Web user interface

**What it contains:**
- Fridge inventory display
- Add/delete item forms
- Recipe generation interface
- Voice query interface
- Responsive design

**When to access:** 
- Open `http://127.0.0.1:3001` in browser
- Automatically served by `backend.py`

---

### 🔴 Model Files (You Need to Add These)

#### `Camera/coco.names` 📄
**Purpose:** List of 80 object classes COCO dataset can detect

**Contains:**
```
person
bicycle
car
...
apple
banana
orange
```

**When needed:** Before running camera detection

---

#### `Camera/ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt` ⚙️
**Purpose:** Model configuration file

**Contains:**
- Neural network architecture
- Layer definitions
- Input/output specifications

**When needed:** Before running camera detection

---

#### `Camera/frozen_inference_graph.pb` 🧠
**Purpose:** Pre-trained neural network weights

**Contains:**
- Trained model parameters (binary file)
- ~20MB in size

**When needed:** Before running camera detection

**How to get these files:**
See `CAMERA_SETUP.md` for download links

---

## 🎯 Common Usage Scenarios

### Scenario 1: Normal Daily Use (No Camera)
```powershell
# Terminal 1: Start backend
.\fridge\Scripts\python.exe backend.py

# Then open browser: http://127.0.0.1:3001
# Add items manually, generate recipes, use voice queries
```

---

### Scenario 2: Using Camera Detection
```powershell
# Terminal 1: Start backend
.\fridge\Scripts\python.exe backend.py

# Terminal 2: Start camera detection
.\fridge\Scripts\python.exe camera_detector.py

# Then open browser: http://127.0.0.1:3001
# Items will be added/removed automatically + manual entry
```

---

### Scenario 3: First-Time Camera Setup
```powershell
# Step 1: Test camera connection
.\fridge\Scripts\python.exe test_camera_stream.py

# Step 2: Check system readiness
.\fridge\Scripts\python.exe test_camera_ready.py

# Step 3: If all good, start backend
.\fridge\Scripts\python.exe backend.py

# Step 4: Start camera detection
.\fridge\Scripts\python.exe camera_detector.py
```

---

### Scenario 4: Troubleshooting Issues
```powershell
# Check system status
.\fridge\Scripts\python.exe test_camera_ready.py

# Test camera separately
.\fridge\Scripts\python.exe test_camera_stream.py

# Check database manually
# MySQL Workbench: SELECT * FROM item;
```

---

## 🔄 Typical Workflow

### Morning: Starting Up
1. Open PowerShell in SmartFridge folder
2. Run backend: `.\fridge\Scripts\python.exe backend.py`
3. (Optional) Run camera: `.\fridge\Scripts\python.exe camera_detector.py`
4. Open browser: `http://127.0.0.1:3001`
5. Use the app!

### Evening: Shutting Down
1. Close browser
2. Stop camera (if running): Press `Ctrl+C` or close window
3. Stop backend: Press `Ctrl+C` in terminal
4. Close terminals

---

## ⚡ Quick Reference Commands

### Start Application
```powershell
# Required
.\fridge\Scripts\python.exe backend.py

# Optional (camera)
.\fridge\Scripts\python.exe camera_detector.py
```

### Testing Commands
```powershell
# Test camera
.\fridge\Scripts\python.exe test_camera_stream.py

# Check readiness
.\fridge\Scripts\python.exe test_camera_ready.py
```

### Database Commands
```powershell
# Run migration (if needed)
.\fridge\Scripts\python.exe migrate_db.py
```

---

## 📊 File Importance Rankings

### ⭐⭐⭐ CRITICAL (Must Have)
1. `backend.py` - Nothing works without this
2. `folder/index.html` - Your web interface
3. `fridge/` folder - Python environment with all packages

### ⭐⭐ IMPORTANT (For Camera Feature)
4. `camera_detector.py` - Camera detection module
5. `Camera/` folder with model files - Required for detection
6. `migrate_db.py` / `add_camera_columns.sql` - Database setup (one-time)

### ⭐ HELPFUL (For Setup & Testing)
7. `test_camera_ready.py` - System verification
8. `test_camera_stream.py` - Camera testing
9. Documentation files - Reference guides

### 📦 CONFIGURATION
10. `requirements.txt` - Package list (already installed)

---

## 🎓 Summary

### Files You MUST Run:
1. **`backend.py`** - Always required

### Files You CAN Run (Optional):
2. **`camera_detector.py`** - Only if using camera detection

### Files You RUN ONCE (Already Done):
3. **`migrate_db.py`** - Database setup (completed)

### Files You RUN for TESTING:
4. **`test_camera_stream.py`** - Camera test
5. **`test_camera_ready.py`** - System check

### Files You READ (Documentation):
6. **`CAMERA_SETUP.md`**
7. **`CAMERA_UPDATE.md`**
8. **`IMPLEMENTATION_SUMMARY.md`**
9. **`EXECUTION_GUIDE.md`** (this file)

### Files You DON'T Run Directly:
10. **`add_camera_columns.sql`** - Use migrate_db.py instead
11. **`requirements.txt`** - Use pip install
12. **`folder/index.html`** - Served by backend.py

---

## ✅ Your Next Actions

### Right Now:
```powershell
# Start the backend
.\fridge\Scripts\python.exe backend.py
```

### Then:
- Open browser: `http://127.0.0.1:3001`
- Test the web interface
- Add items manually
- Generate recipes

### Later (When Ready for Camera):
1. Add model files to `Camera/` folder
2. Run readiness check
3. Test camera stream
4. Start camera detection

---

**That's it! You're ready to use SmartFridge! 🎉**

Questions? Check the documentation files or ask for help!
