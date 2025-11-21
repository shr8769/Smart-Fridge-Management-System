"""
Quick test to verify camera system is ready
"""
import os
import requests

print("=" * 60)
print("CAMERA DETECTION SYSTEM - READINESS CHECK")
print("=" * 60)

# Check 1: Backend connectivity
print("\n1️⃣  Checking backend connection...")
try:
    response = requests.get('http://127.0.0.1:3001/health', timeout=3)
    if response.status_code == 200:
        print("   ✅ Backend is running")
    else:
        print(f"   ⚠️  Backend returned status {response.status_code}")
except Exception as e:
    print(f"   ❌ Cannot connect to backend: {e}")
    print("   → Please start backend.py first!")

# Check 2: Camera folder and files
print("\n2️⃣  Checking Camera files...")
camera_files = [
    'Camera/coco.names',
    'Camera/ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt',
    'Camera/frozen_inference_graph.pb'
]

all_files_exist = True
for file in camera_files:
    if os.path.exists(file):
        print(f"   ✅ {file}")
    else:
        print(f"   ❌ {file} NOT FOUND")
        all_files_exist = False

if not all_files_exist:
    print("\n   → Please ensure all model files are in the Camera/ folder")

# Check 3: Database schema
print("\n3️⃣  Checking database schema...")
try:
    import pymysql
    conn = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='Enjoylife@123',
        database='smartfridge'
    )
    cur = conn.cursor()
    cur.execute("SHOW COLUMNS FROM item LIKE 'source'")
    if cur.fetchone():
        print("   ✅ 'source' column exists")
    else:
        print("   ❌ 'source' column missing - run migrate_db.py")
    
    cur.execute("SHOW COLUMNS FROM item LIKE 'camera_last_seen'")
    if cur.fetchone():
        print("   ✅ 'camera_last_seen' column exists")
    else:
        print("   ❌ 'camera_last_seen' column missing - run migrate_db.py")
    
    conn.close()
except Exception as e:
    print(f"   ⚠️  Database check failed: {e}")

# Check 4: OpenCV
print("\n4️⃣  Checking OpenCV...")
try:
    import cv2
    print(f"   ✅ OpenCV version {cv2.__version__} installed")
except ImportError:
    print("   ❌ OpenCV not installed")
    print("   → Run: pip install opencv-python")

# Check 5: Camera detector script
print("\n5️⃣  Checking camera_detector.py...")
if os.path.exists('camera_detector.py'):
    print("   ✅ camera_detector.py exists")
else:
    print("   ❌ camera_detector.py not found")

print("\n" + "=" * 60)
print("READINESS CHECK COMPLETE")
print("=" * 60)

print("\n📋 Next Steps:")
print("1. Update CAMERA_URL in camera_detector.py with your camera IP")
print("2. Run: .\\fridge\\Scripts\\python.exe camera_detector.py")
print("3. Place objects in front of camera and wait 7 seconds")
print("4. Check the UI to see detected items!")

print("\n💡 Tips:")
print("- Press ESC in camera window to stop detection")
print("- Check console for detection logs")
print("- Manual items and camera items are tracked separately")
print("\n")
