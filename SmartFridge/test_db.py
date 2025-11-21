import pymysql

try:
    print("Connecting to database...")
    conn = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='Enjoylife@123',
        database='smartfridge',
        cursorclass=pymysql.cursors.DictCursor
    )
    print("✅ Connected successfully!")
    
    cur = conn.cursor()
    
    # Check tables
    cur.execute("SHOW TABLES")
    tables = cur.fetchall()
    print(f"\n📊 Tables in database: {tables}")
    
    # Check item table structure
    cur.execute("DESCRIBE item")
    columns = cur.fetchall()
    print("\n📋 Item table structure:")
    for col in columns:
        print(f"  - {col}")
    
    # Try to fetch items
    cur.execute("SELECT * FROM item LIMIT 5")
    items = cur.fetchall()
    print(f"\n📦 Sample items ({len(items)} found):")
    for item in items:
        print(f"  {item}")
    
    conn.close()
    print("\n✅ All tests passed!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
