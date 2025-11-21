# 🗄️ Database Access Guide - Where Your Data Is Stored

## 📍 **Your Database Location & Details**

### **Database Configuration (from backend.py):**

```python
DB_HOST = '127.0.0.1'      # Your local machine (localhost)
DB_PORT = 3306              # Default MySQL port
DB_USER = 'root'            # MySQL username
DB_PASS = 'Enjoylife@123'   # Your MySQL password
DB_NAME = 'smartfridge'     # Database name
```

### **What This Means:**
- ✅ MySQL is running on **your laptop** (127.0.0.1 = localhost)
- ✅ Database name: **`smartfridge`**
- ✅ Table name: **`item`**
- ✅ Port: **3306** (standard MySQL port)

---

## 🔍 **3 Ways to View Your Database**

### **Method 1: MySQL Workbench (Visual Interface)** ⭐ RECOMMENDED

You mentioned you already created the connection using an extension. Here's how to view the data:

#### **Steps:**

1. **Open MySQL Workbench**

2. **Connect to your database:**
   - Click on your existing connection (you already have this set up)
   - Or create new connection:
     - Connection Name: `SmartFridge Local`
     - Hostname: `127.0.0.1`
     - Port: `3306`
     - Username: `root`
     - Password: `Enjoylife@123`

3. **View the data:**
   ```sql
   -- Select the database
   USE smartfridge;
   
   -- View all items in the table
   SELECT * FROM item;
   ```

4. **See camera-detected items specifically:**
   ```sql
   SELECT * FROM item WHERE source = 'camera';
   ```

5. **See manually added items:**
   ```sql
   SELECT * FROM item WHERE source = 'manual';
   ```

6. **Watch data change in real-time:**
   - Keep the query window open
   - Run camera detector
   - Click the **Refresh button** (⟳) or press `Ctrl+R`
   - See new items appear!

---

### **Method 2: VS Code MySQL Extension** 

You mentioned using an extension in VS Code. Here's how to use it:

#### **If you have MySQL extension installed:**

1. **Find the MySQL icon** in VS Code sidebar (left panel)

2. **Your existing connection should be there:**
   - Look for `127.0.0.1:3306` or `smartfridge`

3. **Expand the connection:**
   ```
   ├─ 127.0.0.1:3306
   │  └─ smartfridge
   │     └─ Tables
   │        └─ item  ← Your data is here!
   ```

4. **Right-click on `item` table:**
   - Select **"Show Table Data"** or **"Select Top 1000"**
   - Data appears in editor tab

5. **Run custom queries:**
   - Create new SQL file
   - Write query:
     ```sql
     USE smartfridge;
     SELECT * FROM item ORDER BY added_date DESC;
     ```
   - Right-click → **"Run MySQL Query"**

---

### **Method 3: Command Line (PowerShell)** 

Access MySQL directly from terminal:

#### **Steps:**

1. **Open PowerShell** (you can use your existing terminal)

2. **Connect to MySQL:**
   ```powershell
   mysql -u root -p
   ```

3. **Enter password when prompted:**
   ```
   Enter password: Enjoylife@123
   ```

4. **Select your database:**
   ```sql
   USE smartfridge;
   ```

5. **View all items:**
   ```sql
   SELECT * FROM item;
   ```

6. **View with better formatting:**
   ```sql
   SELECT 
       id,
       label,
       quantity,
       location,
       source,
       expiry_date,
       added_date,
       camera_last_seen
   FROM item
   ORDER BY added_date DESC;
   ```

7. **Exit MySQL:**
   ```sql
   exit;
   ```

---

## 📊 **Useful SQL Queries to Monitor Your Database**

### **1. View All Items:**
```sql
SELECT * FROM item;
```

### **2. View Only Camera-Detected Items:**
```sql
SELECT 
    id,
    label,
    quantity,
    source,
    camera_last_seen,
    added_date
FROM item 
WHERE source = 'camera'
ORDER BY added_date DESC;
```

### **3. View Only Manual Items:**
```sql
SELECT * FROM item WHERE source = 'manual';
```

### **4. Count Items by Source:**
```sql
SELECT 
    source,
    COUNT(*) as count
FROM item 
GROUP BY source;
```

**Example output:**
```
+--------+-------+
| source | count |
+--------+-------+
| manual |     3 |
| camera |     2 |
+--------+-------+
```

### **5. View Recent Camera Activity:**
```sql
SELECT 
    label,
    camera_last_seen,
    TIMESTAMPDIFF(SECOND, camera_last_seen, NOW()) as seconds_ago
FROM item 
WHERE source = 'camera'
ORDER BY camera_last_seen DESC;
```

**This shows:**
- What items camera detected
- When they were last seen
- How many seconds ago

### **6. Watch for Stale Items (about to be removed):**
```sql
SELECT 
    label,
    camera_last_seen,
    TIMESTAMPDIFF(SECOND, camera_last_seen, NOW()) as seconds_since_seen
FROM item 
WHERE source = 'camera'
AND TIMESTAMPDIFF(SECOND, camera_last_seen, NOW()) > 5;
```

**Items with > 7 seconds will be removed by cleanup!**

### **7. View Complete Table Structure:**
```sql
DESCRIBE item;
```

**Shows all columns:**
```
+-------------------+--------------+------+-----+
| Field             | Type         | Null | Key |
+-------------------+--------------+------+-----+
| id                | int          | NO   | PRI |
| label             | varchar(255) | NO   |     |
| quantity          | varchar(50)  | YES  |     |
| location          | varchar(255) | YES  |     |
| expiry_date       | date         | YES  |     |
| added_date        | datetime     | YES  |     |
| source            | varchar(20)  | YES  | MUL |
| camera_last_seen  | datetime     | YES  |     |
+-------------------+--------------+------+-----+
```

---

## 🎬 **Real-Time Database Monitoring**

### **Watch Database Change Live:**

#### **Setup (MySQL Workbench or VS Code):**

1. **Open query window**
2. **Run this query:**
   ```sql
   SELECT 
       id,
       label,
       source,
       added_date,
       camera_last_seen
   FROM item 
   ORDER BY added_date DESC;
   ```

3. **Start your camera detector:**
   ```powershell
   .\fridge\Scripts\python.exe camera_detector.py
   ```

4. **Place an allowed item (apple, orange, banana, carrot) in view**

5. **Wait 7 seconds**

6. **In database window: Click Refresh (⟳) or press Ctrl+R**

7. **🎉 See the new row appear!**

---

## 🔄 **Complete Data Flow Diagram**

```
┌─────────────────────────────────────────────────────────┐
│  ESP32-CAM (http://10.181.154.254:81/stream)          │
│  Captures video feed                                    │
└────────────────────┬────────────────────────────────────┘
                     │ MJPEG Stream
                     ▼
┌─────────────────────────────────────────────────────────┐
│  camera_detector.py (Python Script)                    │
│  - Reads video frames                                   │
│  - Detects objects (orange, banana, apple, carrot)    │
│  - Tracks for 7 seconds                                │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP POST Request
                     │ POST /api/items
                     │ {label: "apple", source: "camera"}
                     ▼
┌─────────────────────────────────────────────────────────┐
│  backend.py (Flask Server on port 3001)               │
│  - Receives camera request                             │
│  - Validates data                                       │
│  - Executes SQL INSERT                                 │
└────────────────────┬────────────────────────────────────┘
                     │ SQL: INSERT INTO item...
                     ▼
┌─────────────────────────────────────────────────────────┐
│  MySQL Server (127.0.0.1:3306)                        │
│  Database: smartfridge                                 │
│  Table: item                                           │
│                                                         │
│  ┌─────────────────────────────────────────────┐     │
│  │ id | label  | source | camera_last_seen     │     │
│  ├────┼────────┼────────┼──────────────────────┤     │
│  │ 1  | milk   | manual | NULL                 │     │
│  │ 2  | eggs   | manual | NULL                 │     │
│  │ 3  | apple  | camera | 2025-11-10 14:32:15  │ ← NEW!
│  └─────────────────────────────────────────────┘     │
└────────────────────┬────────────────────────────────────┘
                     │ SQL: SELECT * FROM item
                     ▼
┌─────────────────────────────────────────────────────────┐
│  backend.py - GET /api/items endpoint                  │
│  - Queries database                                     │
│  - Returns JSON                                         │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP Response (JSON)
                     │ [{id:1,label:"milk"},{id:2,label:"eggs"},{id:3,label:"apple"}]
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Browser (http://127.0.0.1:3001)                      │
│  - JavaScript fetches data every 5 seconds             │
│  - Updates HTML to show items                          │
│  - You see: 🥛 Milk  🥚 Eggs  🍎 Apple               │
└─────────────────────────────────────────────────────────┘
```

---

## 🧪 **Testing Database Operations**

### **Test 1: Manual Addition**

1. **Open browser:** `http://127.0.0.1:3001`
2. **Add item manually:** "Milk"
3. **In MySQL Workbench, run:**
   ```sql
   SELECT * FROM item WHERE label = 'Milk';
   ```
4. **You should see:**
   ```
   id=X, label='Milk', source='manual', camera_last_seen=NULL
   ```

### **Test 2: Camera Addition**

1. **Start camera detector**
2. **Place apple in view**
3. **Wait 7 seconds**
4. **Console shows:** `✅ Added apple to database (ID: Y)`
5. **In MySQL, run:**
   ```sql
   SELECT * FROM item WHERE label = 'apple';
   ```
6. **You should see:**
   ```
   id=Y, label='apple', source='camera', camera_last_seen='2025-11-10 14:32:15'
   ```

### **Test 3: Camera Removal**

1. **Remove apple from camera view**
2. **Wait 7 seconds**
3. **Console shows:** `🗑️ Cleanup removed 1 stale camera items`
4. **In MySQL, run:**
   ```sql
   SELECT * FROM item WHERE label = 'apple';
   ```
5. **Result:** No rows (item deleted)

### **Test 4: Manual Item Stays When Camera Item Removed**

1. **Manually add:** "apple"
2. **Camera detects:** "apple" (now 2 apples in DB)
3. **Remove apple from camera**
4. **In MySQL:**
   ```sql
   SELECT * FROM item WHERE label = 'apple';
   ```
5. **Result:** Only 1 apple remains (the manual one)

---

## 🔧 **Database Troubleshooting**

### **Can't connect to MySQL:**

```powershell
# Check if MySQL is running
Get-Process mysql* 

# Or check Windows Services
Get-Service | Where-Object {$_.Name -like "*mysql*"}
```

**If not running:**
- Open Services (Windows + R → `services.msc`)
- Find "MySQL80" or similar
- Right-click → Start

### **Forgot MySQL password:**

**Current password:** `Enjoylife@123`

**If you need to reset it:**
1. Stop MySQL service
2. Start MySQL with skip-grant-tables
3. Reset password
4. Restart normally

### **Database doesn't exist:**

```sql
-- Check if database exists
SHOW DATABASES;

-- If missing, create it:
CREATE DATABASE smartfridge;

-- Create item table:
USE smartfridge;
CREATE TABLE item (
    id INT AUTO_INCREMENT PRIMARY KEY,
    label VARCHAR(255) NOT NULL,
    quantity VARCHAR(50),
    location VARCHAR(255),
    expiry_date DATE,
    added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(20) DEFAULT 'manual',
    camera_last_seen DATETIME NULL,
    INDEX idx_source (source)
);
```

---

## 📱 **Quick Access Commands**

### **PowerShell - View Data:**
```powershell
# Connect to MySQL
mysql -u root -pEnjoylife@123 smartfridge

# View all items
mysql -u root -pEnjoylife@123 -e "SELECT * FROM item" smartfridge

# View camera items only
mysql -u root -pEnjoylife@123 -e "SELECT * FROM item WHERE source='camera'" smartfridge

# Count items
mysql -u root -pEnjoylife@123 -e "SELECT COUNT(*) as total FROM item" smartfridge
```

### **One-Liner to Monitor:**
```powershell
# Keep watching database every 2 seconds
while ($true) { 
    mysql -u root -pEnjoylife@123 -e "SELECT * FROM item ORDER BY added_date DESC LIMIT 5" smartfridge; 
    Start-Sleep 2; 
    Clear-Host 
}
```

---

## 🎯 **Summary**

### **Your Database Location:**
- **Computer:** Your laptop (127.0.0.1)
- **MySQL Port:** 3306
- **Database Name:** `smartfridge`
- **Table Name:** `item`
- **Username:** `root`
- **Password:** `Enjoylife@123`

### **Best Way to View:**
1. **MySQL Workbench** (GUI) - Most user-friendly
2. **VS Code MySQL Extension** - Integrated with your editor
3. **Command Line** - Quick checks

### **What Gets Added:**
- **Manual additions** → `source='manual'`, `camera_last_seen=NULL`
- **Camera additions** → `source='camera'`, `camera_last_seen=NOW()`

### **What Gets Removed:**
- **Camera items** → Removed after 7s absence
- **Manual items** → Only removed when you click "Remove" button

---

**Need help connecting? Let me know which method you prefer (Workbench, VS Code, or Command Line) and I can give you specific steps!** 🚀
