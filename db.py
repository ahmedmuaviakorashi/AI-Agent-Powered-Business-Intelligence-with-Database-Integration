import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path

def create_database():
    """Create SQLite database with tables and sample data"""
    # Connect to SQLite database (creates file if not exists)
    db_path = "bi_assistant.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop existing tables and views
    cursor.execute("DROP VIEW IF EXISTS campaign_performance")
    cursor.execute("DROP TABLE IF EXISTS budgets")
    cursor.execute("DROP TABLE IF EXISTS marketing_metrics")
    cursor.execute("DROP TABLE IF EXISTS campaign_months")
    cursor.execute("DROP TABLE IF EXISTS products")

    # Create tables
    cursor.execute("""
    CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        category TEXT,
        launch_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE campaign_months (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        month_number INTEGER NOT NULL,
        year INTEGER NOT NULL,
        campaign_name TEXT,
        start_date DATE,
        end_date DATE,
        status TEXT DEFAULT 'active' CHECK (status IN ('active','paused','completed')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(product_id, month_number, year),
        FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE marketing_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_month_id INTEGER,
        impressions INTEGER DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        conversions INTEGER DEFAULT 0,
        revenue REAL DEFAULT 0.00,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(campaign_month_id) REFERENCES campaign_months(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_month_id INTEGER,
        allocated_budget REAL NOT NULL,
        actual_spend REAL DEFAULT 0.00,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(campaign_month_id) REFERENCES campaign_months(id) ON DELETE CASCADE
    )
    """)

    # Insert sample products
    products = [
        ("Product A", "Electronics", "2024-01-15"),
        ("Product B", "Fashion", "2024-02-01"),
        ("Product C", "Home & Garden", "2024-03-10"),
        ("Product D", "Electronics", "2024-01-20"),
        ("Product E", "Fashion", "2024-04-05"),
    ]
    cursor.executemany("INSERT INTO products (name, category, launch_date) VALUES (?, ?, ?)", products)

    # Generate sample campaign data (100 rows)
    for product_id in range(1, 6):  # 5 products
        for month in range(1, 21):  # 20 months = 100 campaigns total
            year = 2024 if month <= 12 else 2025
            m = month if month <= 12 else month - 12
            campaign_name = f"Product {chr(64+product_id)} Campaign {m}/{year}"

            start_date = datetime(year, m, 1)
            end_date = start_date + timedelta(days=27)

            # Insert campaign
            cursor.execute("""
            INSERT INTO campaign_months (product_id, month_number, year, campaign_name, start_date, end_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (product_id, m, year, campaign_name, start_date.date(), end_date.date(), 
                  random.choice(["active", "paused", "completed"])))

            cm_id = cursor.lastrowid

            # Insert marketing metrics with realistic data
            impressions = random.randint(80_000, 300_000)
            clicks = impressions // random.randint(25, 40)
            conversions = clicks // random.randint(15, 25)
            revenue = round(conversions * random.uniform(80, 120), 2)

            cursor.execute("""
            INSERT INTO marketing_metrics (campaign_month_id, impressions, clicks, conversions, revenue)
            VALUES (?, ?, ?, ?, ?)
            """, (cm_id, impressions, clicks, conversions, revenue))

            # Insert budget data
            allocated_budget = random.randint(8000, 18000)
            actual_spend = round(allocated_budget * random.uniform(0.7, 1.1), 2)

            cursor.execute("""
            INSERT INTO budgets (campaign_month_id, allocated_budget, actual_spend)
            VALUES (?, ?, ?)
            """, (cm_id, allocated_budget, actual_spend))

    # Create performance view with calculated metrics
    cursor.execute("""
    CREATE VIEW campaign_performance AS
    SELECT 
        p.name as product_name,
        p.category,
        cm.month_number,
        cm.year,
        cm.campaign_name,
        mm.impressions,
        mm.clicks,
        mm.conversions,
        mm.revenue,
        b.allocated_budget,
        b.actual_spend,
        ROUND(CASE 
            WHEN mm.clicks > 0 AND mm.impressions > 0 
            THEN (CAST(mm.clicks AS REAL) / mm.impressions) * 100 ELSE 0 END, 2) as ctr_percentage,
        ROUND(CASE 
            WHEN b.actual_spend > 0 
            THEN mm.revenue / b.actual_spend ELSE 0 END, 2) as roas,
        ROUND(CASE 
            WHEN b.actual_spend > 0 
            THEN (mm.revenue - b.actual_spend) / b.actual_spend ELSE 0 END, 2) as roi,
        ROUND(CASE 
            WHEN mm.conversions > 0 AND b.actual_spend > 0
            THEN b.actual_spend / mm.conversions ELSE 0 END, 2) as cpa,
        ROUND(CASE 
            WHEN mm.clicks > 0 AND b.actual_spend > 0
            THEN b.actual_spend / mm.clicks ELSE 0 END, 2) as cpc,
        ROUND(CASE 
            WHEN mm.impressions > 0 AND b.actual_spend > 0
            THEN (b.actual_spend / mm.impressions) * 1000 ELSE 0 END, 2) as cpm
    FROM products p
    JOIN campaign_months cm ON p.id = cm.product_id
    JOIN marketing_metrics mm ON cm.id = mm.campaign_month_id
    JOIN budgets b ON cm.id = b.campaign_month_id
    ORDER BY p.name, cm.year, cm.month_number
    """)

    conn.commit()

    # Print summary
    try:
        cursor.execute("SELECT COUNT(*) FROM campaign_months")
        campaign_count = cursor.fetchone()[0]
        print(f"Created {campaign_count} campaign months")
        
        cursor.execute("SELECT COUNT(*) FROM marketing_metrics")
        metrics_count = cursor.fetchone()[0]
        print(f"Created {metrics_count} marketing metrics records")
        
        cursor.execute("SELECT COUNT(*) FROM budgets")
        budget_count = cursor.fetchone()[0]
        print(f"Created {budget_count} budget records")
        
        print(f"Database setup complete at: {db_path}")
        return True
        
    except Exception as e:
        print(f"Error querying database: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = create_database()
    if not success:
        print("Database creation failed!")
        exit(1)
    print("Database created successfully!")