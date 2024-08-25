import psycopg2

try:
    print("start")
    conn = psycopg2.connect(
        dbname="django_url_shortener",
        user="heknt",
        password="1234",
        host="db-1",
        port="5432",
        sslmode="disable"
    )
    print("Connection successful!")
except Exception as e:
    print(f"Connection failed: {e}")