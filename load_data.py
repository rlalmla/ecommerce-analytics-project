"""
load_data.py
============
Loads cleaned merged_data DataFrame into PostgreSQL.
Column names matched to your actual merged_data CSV.

Usage:
    python .\load_data.py
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME", "ecommerce_analytics"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "")
}

# ─────────────────────────────────────────────
# 2. LOAD YOUR CLEANED DATA
# ─────────────────────────────────────────────
def load_merged_data() -> pd.DataFrame:
    df = pd.read_csv(
        r"cleaned_data\merged_data.csv",
        parse_dates=["order_date"]
    )
    return df

# ─────────────────────────────────────────────
# 3. HELPERS
# ─────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def safe_val(v):
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.date() if not pd.isnull(v) else None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v

def df_to_records(df, cols):
    return [tuple(safe_val(row[c]) for c in cols) for _, row in df[cols].iterrows()]

def to_bool_series(s):
    if s.dtype == bool or s.dtype == np.bool_:
        return s
    return s.astype(str).str.lower().isin(["true", "yes", "returned", "1"])

# ─────────────────────────────────────────────
# 4. SCHEMA
# ─────────────────────────────────────────────
def create_schema(conn):
    with open("schema.sql", "r") as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print("✅ Schema created successfully.")

# ─────────────────────────────────────────────
# 5. TIME DIMENSION
# ─────────────────────────────────────────────
def load_time_dimension(conn, df):
    print("⏳ Loading time_dimension ...")
    dates = pd.date_range(df["order_date"].min(), df["order_date"].max(), freq="D")
    festival_map = {
        (10,24):"Diwali",(10,25):"Diwali",(10,26):"Diwali",
        (7,15):"Prime Day",(7,16):"Prime Day",
        (10,15):"Navratri",(10,16):"Navratri",
        (11,27):"Black Friday",(12,25):"Christmas",
        (1,26):"Republic Day",(8,15):"Independence Day",
    }
    records = []
    for d in dates:
        festival = festival_map.get((d.month, d.day))
        records.append((
            d.date(), d.day, d.month, d.strftime("%B"),
            (d.month-1)//3+1, d.year, d.isocalendar()[1],
            d.weekday(), d.strftime("%A"), d.weekday()>=5,
            festival is not None, festival
        ))
    with conn.cursor() as cur:
        execute_values(cur,
            """INSERT INTO time_dimension
               (date_key,day,month,month_name,quarter,year,
                week_of_year,day_of_week,day_name,is_weekend,
                is_festival,festival_name)
               VALUES %s ON CONFLICT DO NOTHING""", records)
    conn.commit()
    print(f"   ✅ {len(records)} dates loaded.")

# ─────────────────────────────────────────────
# 6. CUSTOMERS
# ─────────────────────────────────────────────
def load_customers(conn, df):
    print("⏳ Loading customers ...")
    grp = df.groupby("customer_id")
    agg = grp.agg(
        customer_city    =("customer_city",      "first"),
        customer_state   =("customer_state",     "first"),
        city_tier        =("customer_tier",      "first"),
        age_group        =("customer_age_group", "first"),
        is_prime_member  =("is_prime_member",    "first"),
        first_order_date =("order_date",         "min"),
        last_order_date  =("order_date",         "max"),
        total_orders     =("transaction_id",     "count"),
        total_spent      =("final_amount_inr",   "sum"),
        avg_order_value  =("final_amount_inr",   "mean"),
    ).reset_index()

    agg["rfm_segment"] = pd.cut(
        agg["total_spent"],
        bins=[0, 5000, 20000, 50000, float("inf")],
        labels=["New", "Regular", "Loyal", "Champion"]
    ).astype(str)

    cols = ["customer_id","customer_city","customer_state","city_tier",
            "age_group","is_prime_member","first_order_date","last_order_date",
            "total_orders","total_spent","avg_order_value","rfm_segment"]
    records = df_to_records(agg, cols)
    with conn.cursor() as cur:
        execute_values(cur,
            f"INSERT INTO customers ({','.join(cols)}) VALUES %s ON CONFLICT DO NOTHING",
            records)
    conn.commit()
    print(f"   ✅ {len(records)} customers loaded.")

# ─────────────────────────────────────────────
# 7. PRODUCTS
# ─────────────────────────────────────────────
def load_products(conn, df):
    print("⏳ Loading products ...")
    grp = df.groupby("product_id")
    agg = grp.agg(
        product_name      =("product_name",       "first"),
        category          =("category",           "first"),
        sub_category      =("subcategory",        "first"),
        brand             =("brand",              "first"),
        original_price_inr=("original_price_inr", "first"),
        is_prime_eligible =("is_prime_eligible",  "first"),
        avg_rating        =("customer_rating",    "mean"),
        total_units_sold  =("quantity",           "sum"),
        total_revenue     =("final_amount_inr",   "sum"),
    ).reset_index()

    ret = df.groupby("product_id")["return_status"].apply(
        lambda s: to_bool_series(s).mean()
    ).reset_index()
    ret.columns = ["product_id","return_rate"]
    agg = agg.merge(ret, on="product_id", how="left")

    cols = ["product_id","product_name","category","sub_category","brand",
            "original_price_inr","is_prime_eligible","avg_rating",
            "total_units_sold","total_revenue","return_rate"]
    records = df_to_records(agg, cols)
    with conn.cursor() as cur:
        execute_values(cur,
            f"INSERT INTO products ({','.join(cols)}) VALUES %s ON CONFLICT DO NOTHING",
            records)
    conn.commit()
    print(f"   ✅ {len(records)} products loaded.")

# ─────────────────────────────────────────────
# 8. TRANSACTIONS
# ─────────────────────────────────────────────
def load_transactions(conn, df):
    print("⏳ Loading transactions (~1M rows, please wait) ...")
    df = df.copy()

    # Normalize boolean
    df["is_returned"] = to_bool_series(df["return_status"])

    # Rename columns to match DB schema
    df = df.rename(columns={
        "transaction_id":     "order_id",
        "subcategory":        "sub_category",
        "final_amount_inr":   "total_amount_inr",
        "customer_age_group": "age_group",
        "customer_tier":      "city_tier",
        "order_month":        "month",
        "order_year":         "year",
        "order_quarter":      "quarter",
        "discounted_price_inr": "final_price_inr",
    })

    cols = [
        "order_id","order_date","customer_id","product_id",
        "category","sub_category","brand",
        "quantity","original_price_inr","discount_percent",
        "final_price_inr","total_amount_inr",
        "payment_method","customer_city","customer_state","city_tier",
        "is_prime_member","is_prime_eligible","is_festival_sale",
        "festival_name","delivery_days","customer_rating",
        "is_returned","age_group","year","month","quarter"
    ]

    available = [c for c in cols if c in df.columns]
    missing   = [c for c in cols if c not in df.columns]
    if missing:
        print(f"   ⚠️  Columns not found (skipped): {missing}")

    CHUNK = 10_000
    total = 0
    with conn.cursor() as cur:
        for i in range(0, len(df), CHUNK):
            chunk = df.iloc[i:i+CHUNK]
            records = df_to_records(chunk, available)
            execute_values(cur,
                f"INSERT INTO transactions ({','.join(available)}) VALUES %s ON CONFLICT DO NOTHING",
                records)
            total += len(records)
            print(f"   → {total:,} rows inserted...", end="\r")
    conn.commit()
    print(f"\n   ✅ {total:,} transactions loaded.")

# ─────────────────────────────────────────────
# 9. MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  E-Commerce Analytics — PostgreSQL Data Loader")
    print("=" * 55)

    print("\n📂 Loading merged_data ...")
    merged_data = load_merged_data()
    print(f"   ✅ {len(merged_data):,} rows loaded.")

    print("\n🔌 Connecting to PostgreSQL ...")
    conn = get_connection()
    print("   ✅ Connected.")

    create_schema(conn)
    load_time_dimension(conn, merged_data)
    load_customers(conn, merged_data)
    load_products(conn, merged_data)
    load_transactions(conn, merged_data)

    conn.close()
    print("\n All data loaded successfully!")
  
