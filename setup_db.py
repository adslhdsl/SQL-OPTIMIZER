import sqlite3
import random
from datetime import datetime, timedelta

def setup():
    conn = sqlite3.connect("sample.db")
    cur = conn.cursor()

    # 인덱스 없는 비효율적 스키마 (최적화 실습용)
    cur.executescript("""
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS customers;
        DROP TABLE IF EXISTS products;

        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            email TEXT,
            region TEXT,
            created_at TEXT
        );

        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            price REAL
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            status TEXT,
            ordered_at TEXT
        );
    """)

    # 샘플 데이터 삽입
    regions = ["Seoul", "Busan", "Daegu", "Incheon"]
    categories = ["Electronics", "Clothing", "Food", "Books"]
    statuses = ["pending", "shipped", "delivered", "cancelled"]

    customers = [
        (i, f"Customer_{i}", f"user{i}@email.com",
         random.choice(regions),
         (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 700))).strftime("%Y-%m-%d"))
        for i in range(1, 1001)
    ]
    cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", customers)

    products = [
        (i, f"Product_{i}", random.choice(categories), round(random.uniform(10, 500), 2))
        for i in range(1, 201)
    ]
    cur.executemany("INSERT INTO products VALUES (?,?,?,?)", products)

    orders = [
        (i, random.randint(1, 1000), random.randint(1, 200),
         random.randint(1, 10), random.choice(statuses),
         (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d"))
        for i in range(1, 10001)
    ]
    cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?)", orders)

    conn.commit()
    conn.close()
    print("샘플 DB 생성 완료 (sample.db)")
    print("- customers: 1,000건")
    print("- products: 200건")
    print("- orders: 10,000건")
    print("- 인덱스: 없음 (최적화 실습용)")

if __name__ == "__main__":
    setup()
