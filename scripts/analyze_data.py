#!/usr/bin/env python3
"""
Bank Transaction System Using Apache HBase with Docker
Script: analyze_data.py
Description: Performs comprehensive banking transaction analytics and rule-based
             suspicious activity detection. Fetches records from Apache HBase
             (via REST scanner / fallback to ingested dataset) and exports
             structured JSON and Markdown reports.
"""

import os
import sys
import json
import base64
from datetime import datetime
from collections import defaultdict
import requests

HBASE_REST_URL = os.environ.get("HBASE_REST_URL", "http://localhost:8080")
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "bank_transactions.csv")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def b64_decode(val):
    if not val:
        return ""
    try:
        return base64.b64decode(val.encode("utf-8")).decode("utf-8", errors="replace")
    except Exception:
        return val

def fetch_transactions_from_hbase(batch_limit=15000):
    """
    Fetch records from HBase table 'bank_transactions' using HBase REST scanner.
    Falls back gracefully to CSV dataset if HBase REST is unavailable.
    """
    print(f"[INFO] Attempting to scan 'bank_transactions' from HBase REST at {HBASE_REST_URL}...")
    transactions = []
    
    try:
        # Create a scanner endpoint in HBase REST
        # POST /<table_name>/scanner
        scanner_payload = {
            "batch": 500
        }
        res = requests.put(
            f"{HBASE_REST_URL}/bank_transactions/scanner",
            data=json.dumps(scanner_payload),
            headers=HEADERS,
            timeout=10
        )
        if res.status_code in [201, 200]:
            scanner_url = res.headers.get("Location")
            if not scanner_url:
                scanner_url = f"{HBASE_REST_URL}/bank_transactions/scanner/{res.text.strip()}"
                
            print(f"[INFO] Scanner initialized: {scanner_url}. Pulling records...")
            while len(transactions) < batch_limit:
                scan_res = requests.get(scanner_url, headers=HEADERS, timeout=10)
                if scan_res.status_code == 204 or not scan_res.text:
                    break # Scanner exhausted
                data = scan_res.json()
                rows = data.get("Row", [])
                if not rows:
                    break
                    
                for r in rows:
                    item = {}
                    for cell in r.get("Cell", []):
                        col = b64_decode(cell.get("column", ""))
                        val = b64_decode(cell.get("$", ""))
                        field = col.split(":")[-1] if ":" in col else col
                        item[field] = val
                    if "transaction_id" in item:
                        transactions.append(item)
            
            # Delete scanner when done
            try:
                requests.delete(scanner_url)
            except Exception:
                pass
                
            print(f"[SUCCESS] Retrieved {len(transactions)} transactions directly from HBase table.")
            return transactions
    except Exception as e:
        print(f"[WARNING] HBase REST scan encountered: {e}")
        
    print(f"[INFO] Falling back to reading dataset file at {CSV_PATH}...")
    import csv
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode="r", encoding="utf-8") as f:
            transactions = list(csv.DictReader(f))
        print(f"[INFO] Loaded {len(transactions)} records from local dataset.")
        return transactions

    print("[ERROR] Neither HBase nor CSV dataset could be read.")
    return []

def analyze_transactions(transactions):
    """
    Perform 30+ analytical calculations across banking transactions.
    """
    if not transactions:
        print("[ERROR] No transactions available to analyze.")
        return None, None

    total_count = len(transactions)
    total_amount = 0.0
    amounts = []
    
    type_counts = defaultdict(int)
    type_amounts = defaultdict(float)
    status_counts = defaultdict(int)
    method_counts = defaultdict(int)
    method_amounts = defaultdict(float)
    city_counts = defaultdict(int)
    city_amounts = defaultdict(float)
    branch_counts = defaultdict(int)
    customer_counts = defaultdict(int)
    customer_amounts = defaultdict(float)
    account_counts = defaultdict(int)
    
    daily_counts = defaultdict(int)
    daily_amounts = defaultdict(float)
    monthly_counts = defaultdict(int)
    monthly_amounts = defaultdict(float)
    
    for t in transactions:
        amt = float(t.get("amount", 0.0))
        amounts.append(amt)
        total_amount += amt
        
        ttype = t.get("transaction_type", "Unknown")
        status = t.get("transaction_status", "Unknown")
        method = t.get("payment_method", "Unknown")
        city = t.get("city", "Unknown")
        branch = t.get("branch", "Unknown")
        cust_id = t.get("customer_id", "Unknown")
        cust_name = t.get("customer_name", "Unknown")
        acc_id = t.get("account_id", "Unknown")
        date_str = t.get("transaction_date", "1970-01-01")
        month_str = date_str[:7] if len(date_str) >= 7 else "Unknown"
        
        type_counts[ttype] += 1
        type_amounts[ttype] += amt
        status_counts[status] += 1
        method_counts[method] += 1
        method_amounts[method] += amt
        city_counts[city] += 1
        city_amounts[city] += amt
        branch_counts[branch] += 1
        
        cust_key = f"{cust_id} ({cust_name})"
        customer_counts[cust_key] += 1
        customer_amounts[cust_key] += amt
        account_counts[acc_id] += 1
        
        daily_counts[date_str] += 1
        daily_amounts[date_str] += amt
        monthly_counts[month_str] += 1
        monthly_amounts[month_str] += amt

    # Suspicious Activity Detection (Academic Rule-Based Demonstration)
    # Rules:
    # 1. High-Value Anomaly: Amount >= 300,000
    # 2. Rapid Burst Velocity: More than 3 transactions for same account within a 10-minute window
    # 3. Repeated Failure Anomaly: Multiple consecutive failed transactions
    suspicious_records = []
    
    # Track transactions by account sorted by date & time
    acc_txns = defaultdict(list)
    for t in transactions:
        acc_txns[t.get("account_id")].append(t)
        
    for acc_id, tx_list in acc_txns.items():
        # Sort by date & time
        tx_list.sort(key=lambda x: f"{x.get('transaction_date')} {x.get('transaction_time')}")
        
        for i, tx in enumerate(tx_list):
            reasons = []
            amt = float(tx.get("amount", 0.0))
            
            # Rule 1: High Value Anomaly
            if amt >= 300000.0:
                reasons.append(f"High-Value Anomaly (Amount: ₹{amt:,.2f} exceeds threshold ₹300,000)")
                
            # Rule 2: Rapid Burst Velocity (transactions within 5 minutes)
            burst_count = 1
            if i > 0:
                try:
                    dt_curr = datetime.strptime(f"{tx.get('transaction_date')} {tx.get('transaction_time')}", "%Y-%m-%d %H:%M:%S")
                    dt_prev = datetime.strptime(f"{tx_list[i-1].get('transaction_date')} {tx_list[i-1].get('transaction_time')}", "%Y-%m-%d %H:%M:%S")
                    diff_seconds = abs((dt_curr - dt_prev).total_seconds())
                    if diff_seconds < 180: # within 3 minutes
                        reasons.append(f"High Velocity Burst (Executed within {int(diff_seconds)}s of prior transaction)")
                except Exception:
                    pass

            # Rule 3: Large Transfer on newly failed account
            if tx.get("transaction_type") == "Transfer" and tx.get("transaction_status") == "FAILED" and amt >= 80000:
                reasons.append(f"High-Value Failed Transfer (Possible unauthorized attempt of ₹{amt:,.2f})")

            if reasons:
                suspicious_records.append({
                    "transaction_id": tx.get("transaction_id"),
                    "customer_id": tx.get("customer_id"),
                    "customer_name": tx.get("customer_name"),
                    "account_id": tx.get("account_id"),
                    "transaction_date": tx.get("transaction_date"),
                    "transaction_time": tx.get("transaction_time"),
                    "transaction_type": tx.get("transaction_type"),
                    "amount": amt,
                    "payment_method": tx.get("payment_method"),
                    "status": tx.get("transaction_status"),
                    "risk_reasons": reasons,
                    "risk_score": len(reasons) * 35 + (50 if amt >= 300000 else 15)
                })

    # Sort top entities
    top_customers_vol = sorted(customer_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_customers_amt = sorted(customer_amounts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_accounts_active = sorted(account_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_transactions": total_count,
        "total_volume": round(total_amount, 2),
        "average_amount": round(total_amount / max(total_count, 1), 2),
        "highest_amount": max(amounts) if amounts else 0.0,
        "lowest_amount": min(amounts) if amounts else 0.0,
        "status_distribution": dict(status_counts),
        "type_distribution": dict(type_counts),
        "type_volume": {k: round(v, 2) for k, v in type_amounts.items()},
        "payment_method_distribution": dict(method_counts),
        "payment_method_volume": {k: round(v, 2) for k, v in method_amounts.items()},
        "city_distribution": dict(city_counts),
        "branch_distribution": dict(branch_counts),
        "total_deposits": round(type_amounts.get("Deposit", 0.0), 2),
        "total_withdrawals": round(type_amounts.get("Withdrawal", 0.0) + type_amounts.get("ATM", 0.0), 2),
        "total_transfers": round(type_amounts.get("Transfer", 0.0), 2),
        "top_customers_by_volume": top_customers_vol,
        "top_customers_by_amount": [[k, round(v, 2)] for k, v in top_customers_amt],
        "most_active_accounts": top_accounts_active,
        "suspicious_transactions_count": len(suspicious_records),
        "monthly_summary": {m: {"count": monthly_counts[m], "volume": round(monthly_amounts[m], 2)} for m in sorted(monthly_counts.keys())}
    }

    return summary, suspicious_records

def export_results(summary, suspicious_records):
    """Save analysis metrics as structured JSON files and Markdown report."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    summary_file = os.path.join(RESULTS_DIR, "transaction_summary.json")
    suspicious_file = os.path.join(RESULTS_DIR, "suspicious_transactions.json")
    report_file = os.path.join(REPORTS_DIR, "transaction_analysis_report.md")
    
    with open(summary_file, mode="w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"[SUCCESS] Exported summary to: {summary_file}")
    
    with open(suspicious_file, mode="w", encoding="utf-8") as f:
        json.dump(suspicious_records, f, indent=2)
    print(f"[SUCCESS] Exported {len(suspicious_records)} suspicious records to: {suspicious_file}")

    # Generate Markdown Report
    md_content = f"""# Banking Transaction Analysis & Fraud Detection Report
*Generated on: {summary['generated_at']}*
*Database Engine: Apache HBase on Docker*

## 1. Executive Summary
- **Total Transactions Analyzed:** {summary['total_transactions']:,}
- **Total Financial Volume:** ₹{summary['total_volume']:,.2f}
- **Average Transaction Value:** ₹{summary['average_amount']:,.2f}
- **Highest Transaction:** ₹{summary['highest_amount']:,.2f}
- **Identified Suspicious Records:** {summary['suspicious_transactions_count']:,}

## 2. Transaction Status Distribution
| Status | Transaction Count | Percentage |
| :--- | :--- | :--- |
| SUCCESS | {summary['status_distribution'].get('SUCCESS', 0):,} | {(summary['status_distribution'].get('SUCCESS', 0)/summary['total_transactions'])*100:.2f}% |
| FAILED | {summary['status_distribution'].get('FAILED', 0):,} | {(summary['status_distribution'].get('FAILED', 0)/summary['total_transactions'])*100:.2f}% |
| PENDING | {summary['status_distribution'].get('PENDING', 0):,} | {(summary['status_distribution'].get('PENDING', 0)/summary['total_transactions'])*100:.2f}% |
| REVERSED | {summary['status_distribution'].get('REVERSED', 0):,} | {(summary['status_distribution'].get('REVERSED', 0)/summary['total_transactions'])*100:.2f}% |

## 3. Financial Breakdown by Transaction Type
| Transaction Type | Count | Total Volume (₹) |
| :--- | :--- | :--- |
"""
    for t_type, count in summary["type_distribution"].items():
        vol = summary["type_volume"].get(t_type, 0.0)
        md_content += f"| {t_type} | {count:,} | ₹{vol:,.2f} |\n"

    md_content += f"""
## 4. Top Customers by Transaction Volume
| Customer | Total Transactions |
| :--- | :--- |
"""
    for cust, count in summary["top_customers_by_volume"]:
        md_content += f"| {cust} | {count:,} |\n"

    md_content += f"""
## 5. Rule-Based Suspicious Activity Detection (Academic Demonstration)
> **Disclaimer:** This detection module utilizes rule-based heuristics designed for educational and academic big-data project evaluation.

Total flagged items: **{len(suspicious_records)}**

### Top Flagged Cases
| Transaction ID | Customer | Amount (₹) | Type | Primary Flags |
| :--- | :--- | :--- | :--- | :--- |
"""
    for s in suspicious_records[:15]:
        flags = "; ".join(s["risk_reasons"])
        md_content += f"| {s['transaction_id']} | {s['customer_name']} | ₹{s['amount']:,.2f} | {s['transaction_type']} | {flags} |\n"

    with open(report_file, mode="w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"[SUCCESS] Generated academic analysis report: {report_file}")

if __name__ == "__main__":
    txns = fetch_transactions_from_hbase()
    summary, suspicious = analyze_transactions(txns)
    if summary:
        export_results(summary, suspicious)
