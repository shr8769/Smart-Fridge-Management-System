# Smart Fridge Management System

A full-stack intelligent fridge inventory manager that uses a YOLO-based camera for real-time food detection, automatic inventory updates, expiry tracking, voice assistant, and recipe suggestions. This README is written to be copy/paste-friendly so you can set up the project quickly.

## Highlights (what's implemented)
- YOLO camera detection: detects multiple items per frame (apple, banana, orange, carrot, etc.)
- Automatic add/remove: items added when seen; removed when not seen for a configurable grace period
- Manual inventory management: add / update / delete via web UI
- Expiry tracking: items show expiry and "expiring soon" state
- Voice assistant: natural-language inventory queries, add/remove actions, recipe requests
- Recipe suggestions: Google Gemini API (or local fallback)
- Modern responsive UI with live camera feed
- Edge deployment support: YOLO inference can run on an ESP S3 CAM (ESP32-S3-CAM) for on-device, low-latency detection

## Screenshots
![WhatsApp Image 2025-11-21 at 17 03 56_75d9cdb9](https://github.com/user-attachments/assets/77e93441-4580-4c96-91d4-213f406a2f53)
![WhatsApp Image 2025-11-21 at 17 04 08_3205879e](https://github.com/user-attachments/assets/e3aad266-234c-472c-b8a7-b3e9a15291d8)
![WhatsApp Image 2025-11-21 at 17 04 32_ddda6a1c](https://github.com/user-attachments/assets/439a4efd-03fc-4bd9-ad77-f89605f54bf1)
![WhatsApp Image 2025-11-21 at 17 04 51_c6875f01](https://github.com/user-attachments/assets/d99d8e96-df2b-423c-8cb1-0a26c2e33008)
![WhatsApp Image 2025-11-21 at 17 14 25_9d9b3ce1](https://github.com/user-attachments/assets/4a9b776c-feb8-40cb-89cf-dde2c74ae9e6)
![WhatsApp Image 2025-11-21 at 17 17 36_78feeeef](https://github.com/user-attachments/assets/3a89139f-694b-4571-ad9e-8cbd79a651d2)
![WhatsApp Image 2025-11-21 at 17 22 18_8e9d5d25](https://github.com/user-attachments/assets/09d2df4e-290e-4665-b533-a0ef69c7848b)
![WhatsApp Image 2025-11-21 at 18 05 37_8b4367b8](https://github.com/user-attachments/assets/40f3f21c-146a-4ab5-b7e5-938e1dfe596d)


## Tech stack
- Backend: Python (Flask)
- Detection: YOLO (OpenCV integration)
- Database: MySQL (SQLite recommended for quick local testing)
- AI: Google Gemini API (recipes) / local fallback
- TTS: gTTS
- Frontend: HTML / CSS / JS
- Misc: Flask-CORS, python-dotenv

## Edge Deployment (ESP32-S3-CAM)
This project supports deploying a lightweight YOLO-based model to an ESP32-S3-CAM (referred to here as "ESP S3 CAM") for on-device inference. Running inference at the edge reduces network bandwidth, lowers latency, and offloads continuous frame processing from the backend.

## Repo layout (key files)
~~~
SmartFridge/
│   .env
│   add_camera_columns.sql
│   add_missing_item_columns.sql
│   align_for_backend.sql
│   AUTOMATED_CAMERA_GUIDE.md
│   backend.py
│   camera_detector.py
│   CAMERA_FILTER_UPDATE.md
│   CAMERA_NETWORK_GUIDE.md
│   CAMERA_SETUP.md
│   camera_stream.log
│   camera_stream_server.py
│   CAMERA_UPDATE.md
│   create_db.sql
│   DATABASE_ACCESS_GUIDE.md
│   EXECUTION_GUIDE.md
│   find_password.py
│   fix_recipes_schema.sql
│   IMPLEMENTATION_SUMMARY.md
│   migrate_db.py
│   README.md
│   reference_backend.py
│   requirements.txt
│   test_camera_ready.py
│   test_camera_stream.py
│   test_db.py
│
├── Camera/
├── folder/
├── fridge/
~~~
## Quick setup (copy/paste)

1) Clone the repo
```
git clone https://github.com/shr8769/Smart-Fridge-Management-System.git
cd Smart-Fridge-Management-System/SmartFridge
```

2) Create and activate a virtualenv
```
python -m venv venv
# macOS / Linux
source venv/bin/activate
# Windows
venv\Scripts\activate
```

3) Install dependencies
```
pip install -r requirements.txt
```

4) Configure environment variables
- Copy the example .env.example to .env and edit values:
```
cp .env.example .env
# or on Windows PowerShell
copy .env.example .env
```
- At minimum set:
  - MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB (or DATABASE_URL)
  - GEMINI_API_KEY (optional)
  - DETECTOR_SOURCE (0 for webcam)

5) Create the database schema (MySQL example)
```
# using mysql client
mysql -u <user> -p <dbname> < sql/schema_mysql.sql
```
(There is also an sqlite-friendly schema included if you prefer local testing.)

6) Start backend
```
# Example (Flask)
export FLASK_APP=backend.py
export FLASK_ENV=development
# or on Windows
# set FLASK_APP=backend.py
flask run --host=0.0.0.0 --port=5000
```

7) Start detector (separate terminal)
```
python camera_detector.py --model models/yolov5s.pt --source 0 --backend-url http://localhost:5000/api/detections
```

8) Open UI
- Open your browser to http://localhost:3001 (or the address/port configured by the frontend)

## API Endpoints (implemented)
- GET /api/items
- POST /api/items
- DELETE /api/items/<id>
- POST /api/camera/heartbeat
- POST /api/camera/cleanup
- POST /api/detections
- GET /api/recipes?available_only=true
- POST /api/generate_recipe
- POST /api/voice/query
- POST /api/voice/tts

(See backend.py for exact routes and payload structures.)

## Notes & tips
- For local development you can use SQLite by setting DATABASE_URL=sqlite:///smartfridge.db
- If detection produces duplicates, tune detector debounce (N-frame threshold) or last_seen grace period.
- For production, use a persistent DB (Postgres/MySQL), add authentication, and run the detector in a container or on an edge device.



## Contributing
- Fork → branch → PR. Add tests for inventory and detection reconciliation.

## License
MIT. Add a LICENSE file at repo root.

Maintainer: shr8769
