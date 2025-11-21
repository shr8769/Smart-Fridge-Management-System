"""
Simple test to verify ESP32-CAM MJPEG stream works
Run this BEFORE running the full camera_detector.py
"""
import cv2

# Your ESP32-CAM stream URL
CAMERA_URL = 'http://10.181.154.254:81/stream'

print("=" * 60)
print("ESP32-CAM MJPEG Stream Test")
print("=" * 60)
print(f"Camera URL: {CAMERA_URL}")
print("\nAttempting to connect...\n")

# Try to open the stream
cap = cv2.VideoCapture(CAMERA_URL)

if not cap.isOpened():
    print("❌ Cannot open camera stream")
    print("\nTroubleshooting:")
    print("1. Check ESP32-CAM is powered on")
    print("2. Verify IP address is correct")
    print("3. Test URL in browser (should show video)")
    print("4. Ensure both devices are on same network")
    exit(1)

print("✅ Camera stream opened successfully!")
print("\nShowing video feed...")
print("Press ESC to close\n")

frame_count = 0
cv2.namedWindow('ESP32-CAM Test', cv2.WINDOW_AUTOSIZE)

try:
    while True:
        ret, img = cap.read()
        
        if not ret:
            print("⚠️  Failed to grab frame")
            break
        
        frame_count += 1
        
        # Display frame count on video
        cv2.putText(img, f"Frame: {frame_count}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.imshow('ESP32-CAM Test', img)
        
        # ESC to exit
        if cv2.waitKey(1) & 0xFF == 27:
            print("\n✅ Test completed successfully!")
            print(f"Total frames received: {frame_count}")
            break

except KeyboardInterrupt:
    print("\n⏹️  Test interrupted")

finally:
    cap.release()
    cv2.destroyAllWindows()
    print("✅ Camera test finished")
