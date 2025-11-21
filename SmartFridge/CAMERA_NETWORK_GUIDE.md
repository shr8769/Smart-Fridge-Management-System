# 🎥 Camera Configuration for SmartFridge

## Quick Network Switch Guide

### Current Camera URL:
```
http://10.181.154.254:81/stream
```

---

## 🔧 How to Update Camera IP After Network Change

### Option 1: Update ESP32-CAM IP (Recommended)

**Step 1: Find your ESP32-CAM's new IP address**

**Method A - Check Router:**
- Log into your WiFi router admin panel
- Look for connected devices
- Find device named "ESP32" or similar
- Note the IP address (e.g., `192.168.1.150`)

**Method B - Use IP Scanner:**
```powershell
# Install: choco install advanced-ip-scanner
# Or download from: https://www.advanced-ip-scanner.com/
# Scan your network and look for ESP32-CAM
```

**Method C - Serial Monitor (if you have USB cable):**
- Connect ESP32-CAM to PC via USB
- Open Arduino IDE Serial Monitor
- Reset the ESP32-CAM
- IP address will be printed on startup

**Step 2: Update the camera URL**

Edit `camera_stream_server.py` (line ~11):
```python
CAMERA_URL = 'http://YOUR_NEW_IP:81/stream'  # Change this!
```

Example:
```python
CAMERA_URL = 'http://192.168.1.150:81/stream'  # New network IP
```

**Step 3: Restart backend**
```powershell
# Stop backend (Ctrl+C)
# Start again
.\fridge\Scripts\python.exe backend.py
```

---

### Option 2: Use PC Webcam as Temporary Fallback

If you don't have access to ESP32-CAM, use your laptop's webcam:

Edit `camera_stream_server.py` (line ~18):
```python
USE_WEBCAM_FALLBACK = True   # Change from False to True
WEBCAM_INDEX = 0              # 0 = default webcam, 1 = external webcam
```

**Note:** Webcam won't show ESP32-CAM stream, but detection will still work with whatever is in front of your laptop camera.

---

## 🌐 Common Network Scenarios

### Home Network (Router)
- Format: `192.168.1.XXX` or `192.168.0.XXX`
- Example: `http://192.168.1.150:81/stream`

### Mobile Hotspot
- Format: `192.168.43.XXX` or `172.20.10.XXX`
- Example: `http://192.168.43.200:81/stream`

### College/Office Network
- Format: `10.XXX.XXX.XXX`
- Example: `http://10.181.154.254:81/stream` (your current)

### Static IP (if configured)
- Use whatever you set in ESP32-CAM code
- Example: `http://192.168.1.100:81/stream`

---

## 🧪 Test Camera Connection

### Test 1: Browser Test
```
http://YOUR_CAMERA_IP:81/stream
```
If you see video → IP is correct!
If error → IP is wrong or camera is off

### Test 2: Ping Test
```powershell
ping YOUR_CAMERA_IP
```
If replies → Camera is reachable
If timeout → Camera is off or wrong IP

### Test 3: Direct Stream Test
```powershell
# Open in browser
start http://10.181.154.254:81/stream
```

---

## 🔄 Quick Fix Checklist

When camera stops working after network change:

- [ ] ESP32-CAM is powered on
- [ ] ESP32-CAM is connected to same WiFi network as your PC
- [ ] Found new IP address of ESP32-CAM
- [ ] Updated `CAMERA_URL` in `camera_stream_server.py`
- [ ] Restarted backend (`.\fridge\Scripts\python.exe backend.py`)
- [ ] Clicked "Start Camera Detection" button in browser

---

## 📝 Current Network Info

To check your PC's current network:
```powershell
ipconfig
```

Look for:
```
Wireless LAN adapter Wi-Fi:
   IPv4 Address. . . . . . . . . . . : 10.181.154.123
   Default Gateway . . . . . . . . . : 10.181.154.1
```

Your ESP32-CAM should be on same subnet (e.g., `10.181.154.XXX`)

---

## 💡 Pro Tip: Set Static IP for ESP32-CAM

To avoid IP changes every network switch, configure static IP in ESP32-CAM code:

```cpp
// In your ESP32-CAM Arduino sketch:
IPAddress local_IP(192, 168, 1, 100);  // Static IP
IPAddress gateway(192, 168, 1, 1);     // Your router IP
IPAddress subnet(255, 255, 255, 0);

WiFi.config(local_IP, gateway, subnet);
```

Then update once:
```python
CAMERA_URL = 'http://192.168.1.100:81/stream'  # Never changes!
```

---

## 🆘 Troubleshooting

### Problem: Camera worked before, now ERR_CONNECTION_REFUSED

**Solution:** Network changed, IP changed
1. Find new ESP32-CAM IP
2. Update `camera_stream_server.py`
3. Restart backend

### Problem: Can't find ESP32-CAM IP

**Solution:** Use webcam temporarily
1. Set `USE_WEBCAM_FALLBACK = True`
2. Restart backend
3. Camera detection works with PC webcam

### Problem: Wrong network, can't connect

**Solution:** Connect to same WiFi
- Ensure PC and ESP32-CAM are on SAME network
- Check WiFi name (SSID) on both devices

---

## 📍 Your Network History

Keep track of IPs for different locations:

| Location | Network Name | ESP32-CAM IP | Date |
|----------|-------------|--------------|------|
| College Lab | ? | `10.181.154.254` | Nov 10, 2025 |
| Home | ? | `192.168.1.XXX` | - |
| Mobile Hotspot | ? | `192.168.43.XXX` | - |

**Fill this in as you use different networks!**

---

Last updated: November 10, 2025
