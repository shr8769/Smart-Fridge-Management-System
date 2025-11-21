import pymysql

passwords_to_try = [
    'enjoylife@123',
    'Enjoylife@123',
    'EnjoyLife@123',
    'enjoyLife@123'
]

print("Testing MySQL passwords...")
for pwd in passwords_to_try:
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password=pwd,
            database='smartfridge',
            connect_timeout=2
        )
        print(f"✅ SUCCESS! Password is: {pwd}")
        conn.close()
        break
    except pymysql.err.OperationalError as e:
        print(f"❌ Failed with '{pwd}': {e.args[1]}")
    except Exception as e:
        print(f"❌ Error with '{pwd}': {e}")
