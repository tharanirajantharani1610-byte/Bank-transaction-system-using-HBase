#!/usr/bin/env python3
"""
Bank Transaction System Using Apache HBase with Docker
Script: load_data.py
Description: Ingests banking transactions from CSV into Apache HBase running in Docker.
             Uses the official HBase REST (Stargate) API with high-throughput batching,
             Base64 encoding, schema validation, and progress tracking.
"""

import os
import csv
import sys
import time
import json
import base64
import subprocess
import requests

HBASE_REST_URL = os.environ.get("HBASE_REST_URL", "http://localhost:8080")
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "bank_transactions.csv")
BATCH_SIZE = 100 # Batch size for HTTP PUT requests

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def b64(val):
    """Encode string or number to Base64 string for HBase REST protocol."""
    if val is None:
        val = ""
    return base64.b64encode(str(val).encode("utf-8")).decode("utf-8")

def b64_decode(val):
    """Decode Base64 string returned by HBase REST protocol."""
    if not val:
        return ""
    return base64.b64decode(val.encode("utf-8")).decode("utf-8", errors="replace")

def wait_for_hbase(timeout=180):
    """Wait until HBase REST API becomes available."""
    print(f"[INFO] Checking HBase connection at {HBASE_REST_URL}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            res = requests.get(f"{HBASE_REST_URL}/version/cluster", headers=HEADERS, timeout=5)
            if res.status_code in [200, 204]:
                print(f"[SUCCESS] HBase REST cluster is online and responding! (Version: {res.text.strip()})")
                return True
        except requests.exceptions.RequestException:
            pass
        
        # Also check root or status
        try:
            res = requests.get(f"{HBASE_REST_URL}/status/cluster", headers=HEADERS, timeout=5)
            if res.status_code in [200, 204]:
                print(f"[SUCCESS] HBase REST cluster is online and responding!")
                return True
        except requests.exceptions.RequestException:
            pass

        time.sleep(4)
        elapsed = int(time.time() - start_time)
        print(f"  ...waiting for HBase daemons to initialize ({elapsed}s elapsed)")
    
    print("[ERROR] Timeout reached while waiting for HBase.")
    return False

def ensure_tables_exist():
    """Verify tables exist in HBase; create them via REST or hbase shell if missing."""
    tables_to_create = {
        "bank_transactions": ["customer", "transaction", "account", "location", "payment"],
        "customer_accounts": ["personal", "location", "balance"],
        "transaction_summary": ["stats"]
    }
    
    for table_name, families in tables_to_create.items():
        try:
            # Check if table exists
            check_res = requests.get(f"{HBASE_REST_URL}/{table_name}/schema", headers=HEADERS, timeout=5)
            if check_res.status_code == 200:
                print(f"[INFO] Table '{table_name}' already exists.")
                continue
        except Exception:
            pass
            
        print(f"[INFO] Creating table '{table_name}' with column families {families}...")
        # Create table via REST schema endpoint
        schema_payload = {
            "name": table_name,
            "ColumnSchema": [{"name": cf} for cf in families]
        }
        try:
            create_res = requests.put(
                f"{HBASE_REST_URL}/{table_name}/schema",
                data=json.dumps(schema_payload),
                headers=HEADERS,
                timeout=15
            )
            if create_res.status_code in [200, 201]:
                print(f"[SUCCESS] Created table '{table_name}' via HBase REST API.")
                continue
        except Exception as e:
            print(f"[WARNING] REST schema creation for '{table_name}' returned error: {e}")
        
        # Fallback: Create table via docker exec hbase shell
        print(f"[INFO] Running fallback table creation via Docker HBase Shell for '{table_name}'...")
        cf_args = ", ".join([f"'{cf}'" for cf in families])
        cmd = f"docker exec -i hbase-master hbase shell -n"
        input_script = f"create '{table_name}', {cf_args}\nexit\n"
        try:
            proc = subprocess.run(
                ["docker", "exec", "-i", "hbase-master", "hbase", "shell", "-n"],
                input=input_script.encode("utf-8"),
                capture_output=True,
                timeout=30
            )
            print(f"[INFO] HBase shell table creation output:\n{proc.stdout.decode('utf-8', errors='replace')}")
        except Exception as e:
            print(f"[ERROR] Could not create table '{table_name}' via docker exec: {e}")

def load_data(limit=None):
    """Read CSV dataset and load transactions into HBase in batches."""
    if not os.path.exists(CSV_PATH):
        print(f"[ERROR] Dataset file not found at: {CSV_PATH}")
        print("Please run scripts/generate_data.py first.")
        return False
        
    print(f"[INFO] Reading dataset from {CSV_PATH}...")
    with open(CSV_PATH, mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        
    if limit:
        reader = reader[:limit]
        
    total_records = len(reader)
    print(f"[INFO] Ingesting {total_records} records into HBase...")
    
    start_time = time.time()
    txn_batch = []
    account_tracker = {}
    
    total_inserted = 0
    
    for idx, row in enumerate(reader, 1):
        # Row key: <customer_id>#<transaction_date>#<transaction_id>
        row_key = f"{row['customer_id']}#{row['transaction_date']}#{row['transaction_id']}"
        
        cells = [
            # customer CF
            {"column": b64("customer:customer_id"), "$": b64(row["customer_id"])},
            {"column": b64("customer:customer_name"), "$": b64(row["customer_name"])},
            {"column": b64("customer:account_type"), "$": b64(row["account_type"])},
            # transaction CF
            {"column": b64("transaction:transaction_id"), "$": b64(row["transaction_id"])},
            {"column": b64("transaction:transaction_type"), "$": b64(row["transaction_type"])},
            {"column": b64("transaction:amount"), "$": b64(row["amount"])},
            {"column": b64("transaction:transaction_date"), "$": b64(row["transaction_date"])},
            {"column": b64("transaction:transaction_time"), "$": b64(row["transaction_time"])},
            {"column": b64("transaction:transaction_status"), "$": b64(row["transaction_status"])},
            {"column": b64("transaction:description"), "$": b64(row["description"])},
            # account CF
            {"column": b64("account:account_id"), "$": b64(row["account_id"])},
            {"column": b64("account:balance_after_transaction"), "$": b64(row["balance_after_transaction"])},
            {"column": b64("account:sender_account"), "$": b64(row["sender_account"])},
            {"column": b64("account:receiver_account"), "$": b64(row["receiver_account"])},
            # location CF
            {"column": b64("location:branch"), "$": b64(row["branch"])},
            {"column": b64("location:city"), "$": b64(row["city"])},
            # payment CF
            {"column": b64("payment:payment_method"), "$": b64(row["payment_method"])},
        ]
        
        txn_batch.append({
            "key": b64(row_key),
            "Cell": cells
        })
        
        # Track latest customer account details
        acc_key = f"{row['customer_id']}#{row['account_id']}"
        account_tracker[acc_key] = {
            "key": b64(acc_key),
            "Cell": [
                {"column": b64("personal:customer_name"), "$": b64(row["customer_name"])},
                {"column": b64("personal:account_type"), "$": b64(row["account_type"])},
                {"column": b64("location:branch"), "$": b64(row["branch"])},
                {"column": b64("location:city"), "$": b64(row["city"])},
                {"column": b64("balance:current_balance"), "$": b64(row["balance_after_transaction"])},
                {"column": b64("balance:last_transaction_date"), "$": b64(row["transaction_date"])},
                {"column": b64("balance:status"), "$": b64("ACTIVE")}
            ]
        }
        
        # Flush batch when limit reached
        if len(txn_batch) >= BATCH_SIZE or idx == total_records:
            payload = {"Row": txn_batch}
            try:
                put_res = requests.put(
                    f"{HBASE_REST_URL}/bank_transactions/false-row-key",
                    data=json.dumps(payload),
                    headers=HEADERS,
                    timeout=20
                )
                if put_res.status_code in [200, 204]:
                    total_inserted += len(txn_batch)
                else:
                    print(f"[WARNING] Batch insert returned status {put_res.status_code}: {put_res.text[:120]}")
            except Exception as e:
                print(f"[ERROR] Batch insertion failed: {e}")
                
            txn_batch = []
            
            # Print progress every 1000 records or at completion
            if total_inserted % 1000 == 0 or total_inserted == total_records:
                pct = (total_inserted / total_records) * 100
                speed = total_inserted / max(time.time() - start_time, 0.001)
                print(f"[PROGRESS] Inserted {total_inserted}/{total_records} records ({pct:.1f}%) - Speed: {speed:.1f} rows/sec")

    # Ingest customer_accounts in batches
    print(f"[INFO] Ingesting {len(account_tracker)} unique customer accounts...")
    acc_list = list(account_tracker.values())
    for i in range(0, len(acc_list), BATCH_SIZE):
        batch = acc_list[i:i + BATCH_SIZE]
        payload = {"Row": batch}
        try:
            requests.put(
                f"{HBASE_REST_URL}/customer_accounts/false-row-key",
                data=json.dumps(payload),
                headers=HEADERS,
                timeout=20
            )
        except Exception as e:
            print(f"[WARNING] Account batch insertion error: {e}")
            
    elapsed = time.time() - start_time
    print(f"\n=======================================================")
    print(f"[SUCCESS] Ingestion completed in {elapsed:.2f} seconds!")
    print(f"Total Transactions loaded: {total_inserted}")
    print(f"Total Customer Accounts loaded: {len(account_tracker)}")
    print(f"HBase Table: 'bank_transactions'")
    print(f"HBase Table: 'customer_accounts'")
    print(f"=======================================================\n")
    return True

if __name__ == "__main__":
    if not wait_for_hbase():
        print("[ERROR] Could not connect to HBase. Ensure Docker container is running.")
        sys.exit(1)
        
    ensure_tables_exist()
    load_data()
