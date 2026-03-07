import sqlite3
import pandas as pd
import numpy as np
import os
import json

DB_PATH = "/app/brain/04_Output/real_estate.db"

def refine_data():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    
    if df.empty:
        print("No data to refine.")
        return

    # 1. Outlier Detection (for trade_price)
    # Using IQR (Interquartile Range) method
    Q1 = df['trade_price'].quantile(0.25)
    Q3 = df['trade_price'].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    # Detect outliers
    outliers = df[(df['trade_price'] < lower_bound) | (df['trade_price'] > upper_bound)]
    print(f"Detected {len(outliers)} outliers.")

    # 2. Correction (Substitute with mean of the municipality if extreme)
    # For now, let's just flag or remove extreme outliers to maintain quality
    df_clean = df[(df['trade_price'] >= lower_bound) & (df['trade_price'] <= upper_bound)]
    
    # Alternatively, replace with mean
    # df.loc[df['trade_price'] > upper_bound, 'trade_price'] = df['trade_price'].mean()

    # Save cleaned data back or to a processed table
    df_clean.to_sql("transactions_refined", conn, if_exists="replace", index=False)
    conn.close()
    print("✅ Data refinement complete. Refined table: transactions_refined")

if __name__ == "__main__":
    refine_data()
