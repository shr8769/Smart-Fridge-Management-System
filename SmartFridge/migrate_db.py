import pymysql

# Update database schema for camera detection
try:
    conn = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='Enjoylife@123',
        database='smartfridge'
    )
    cur = conn.cursor()
    
    print("Updating database schema for camera detection...")
    
    # Add source column
    try:
        cur.execute("""
            ALTER TABLE item 
            ADD COLUMN source VARCHAR(20) DEFAULT 'manual'
        """)
        print("✅ Added 'source' column")
    except Exception as e:
        if 'Duplicate column' in str(e):
            print("ℹ️  'source' column already exists")
        else:
            print(f"⚠️  Error adding source column: {e}")
    
    # Add camera_last_seen column
    try:
        cur.execute("""
            ALTER TABLE item 
            ADD COLUMN camera_last_seen DATETIME NULL
        """)
        print("✅ Added 'camera_last_seen' column")
    except Exception as e:
        if 'Duplicate column' in str(e):
            print("ℹ️  'camera_last_seen' column already exists")
        else:
            print(f"⚠️  Error adding camera_last_seen column: {e}")
    
    # Add index
    try:
        cur.execute("""
            ALTER TABLE item 
            ADD INDEX idx_source (source)
        """)
        print("✅ Added index on 'source' column")
    except Exception as e:
        if 'Duplicate key' in str(e):
            print("ℹ️  Index already exists")
        else:
            print(f"⚠️  Error adding index: {e}")
    
    conn.commit()
    
    # Show updated schema
    cur.execute("DESCRIBE item")
    columns = cur.fetchall()
    print("\n✅ Updated table structure:")
    for col in columns:
        print(f"  - {col[0]}: {col[1]}")
    
    conn.close()
    print("\n✅ Database schema updated successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
