#!/usr/bin/env python3
"""
Bank Transaction System Using Apache HBase with Docker
Backend REST API Server
File: backend/app.py
"""

import os
import sys
import json
import base64
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests

app = Flask(__name__, static_folder="../dashboard", static_url_path="")
CORS(app)

HBASE_REST_URL = os.environ.get("HBASE_REST_URL", "http://localhost:8080")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def b64_encode(val):
    if val is None:
        val = ""
    return base64.b64encode(str(val).encode("utf-8")).decode("utf-8")

def b64_decode(val):
    if not val:
        return ""
    try:
        return base64.b64decode(val.encode("utf-8")).decode("utf-8", errors="replace")
    except Exception:
        return str(val)

def parse_hbase_row(row_obj):
    """Convert an HBase JSON row item into a clean dictionary."""
    row_key = b64_decode(row_obj.get("key", ""))
    item = {"row_key": row_key}
    for cell in row_obj.get("Cell", []):
        col = b64_decode(cell.get("column", ""))
        val = b64_decode(cell.get("$", ""))
        field = col.split(":")[-1] if ":" in col else col
        item[field] = val
        
    if "amount" in item:
        try:
            item["amount"] = float(item["amount"])
        except ValueError:
            pass
    if "balance_after_transaction" in item:
        try:
            item["balance_after_transaction"] = float(item["balance_after_transaction"])
        except ValueError:
            pass
            
    return item

@app.route("/")
def serve_dashboard():
    """Serve Dashboard index.html."""
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/health", methods=["GET"])
def health():
    """Verify HBase cluster connectivity."""
    try:
        res = requests.get(f"{HBASE_REST_URL}/version/cluster", headers=HEADERS, timeout=4)
        if res.status_code in [200, 204]:
            return jsonify({
                "status": "healthy",
                "hbase_connected": True,
                "hbase_version": res.text.strip(),
                "hbase_endpoint": HBASE_REST_URL
            })
    except Exception as e:
        return jsonify({
            "status": "degraded",
            "hbase_connected": False,
            "error": str(e)
        }), 503

@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    """
    List transactions from HBase with pagination and optional filtering.
    Query parameters:
    - limit: int (default: 50, max: 200)
    - customer_id: str (filter by customer prefix)
    - status: str (filter by transaction status)
    - type: str (filter by transaction type)
    """
    limit = min(int(request.args.get("limit", 50)), 200)
    customer_id = request.args.get("customer_id", "").strip()
    status_filter = request.args.get("status", "").strip().upper()
    type_filter = request.args.get("type", "").strip().capitalize()
    
    scanner_spec = {"batch": limit * 2}
    if customer_id:
        # Prefix filter for customer
        scanner_spec["startRow"] = b64_encode(f"{customer_id}#")
        scanner_spec["stopRow"] = b64_encode(f"{customer_id}~")
        
    transactions = []
    try:
        # Open HBase Scanner
        scan_init = requests.put(
            f"{HBASE_REST_URL}/bank_transactions/scanner",
            data=json.dumps(scanner_spec),
            headers=HEADERS,
            timeout=5
        )
        if scan_init.status_code in [200, 201]:
            scanner_url = scan_init.headers.get("Location")
            if not scanner_url:
                scanner_url = f"{HBASE_REST_URL}/bank_transactions/scanner/{scan_init.text.strip()}"
                
            res = requests.get(scanner_url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                rows = res.json().get("Row", [])
                for r in rows:
                    tx = parse_hbase_row(r)
                    if status_filter and tx.get("transaction_status", "").upper() != status_filter:
                        continue
                    if type_filter and tx.get("transaction_type", "").capitalize() != type_filter:
                        continue
                    transactions.append(tx)
                    if len(transactions) >= limit:
                        break
                        
            # Close scanner
            try:
                requests.delete(scanner_url)
            except Exception:
                pass
                
        return jsonify({
            "count": len(transactions),
            "limit": limit,
            "transactions": transactions
        })
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve transactions from HBase: {str(e)}"}), 500

@app.route("/api/transactions/<transaction_id>", methods=["GET"])
def get_transaction_by_id(transaction_id):
    """
    Find a specific transaction by scanning for matching transaction_id.
    """
    try:
        # Scanner to locate transaction
        scanner_spec = {"batch": 500}
        scan_init = requests.put(
            f"{HBASE_REST_URL}/bank_transactions/scanner",
            data=json.dumps(scanner_spec),
            headers=HEADERS,
            timeout=5
        )
        if scan_init.status_code in [200, 201]:
            scanner_url = scan_init.headers.get("Location") or f"{HBASE_REST_URL}/bank_transactions/scanner/{scan_init.text.strip()}"
            while True:
                res = requests.get(scanner_url, headers=HEADERS, timeout=8)
                if res.status_code == 204 or not res.text:
                    break
                rows = res.json().get("Row", [])
                for r in rows:
                    tx = parse_hbase_row(r)
                    if tx.get("transaction_id") == transaction_id:
                        try:
                            requests.delete(scanner_url)
                        except Exception:
                            pass
                        return jsonify({"found": True, "transaction": tx})
            try:
                requests.delete(scanner_url)
            except Exception:
                pass
                
        return jsonify({"found": False, "message": f"Transaction '{transaction_id}' not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/transactions", methods=["POST"])
def create_transaction():
    """
    CRUD: CREATE operation.
    Insert a new banking transaction record into HBase.
    """
    data = request.json or {}
    cust_id = data.get("customer_id")
    amt = data.get("amount")
    txn_type = data.get("transaction_type", "Payment")
    
    if not cust_id or amt is None:
        return jsonify({"error": "Missing required fields: customer_id, amount"}), 400
        
    txn_id = data.get("transaction_id", f"TXN{int(datetime.now().timestamp() * 1000)}")
    txn_date = data.get("transaction_date", datetime.now().strftime("%Y-%m-%d"))
    txn_time = data.get("transaction_time", datetime.now().strftime("%H:%M:%S"))
    
    row_key = f"{cust_id}#{txn_date}#{txn_id}"
    
    cells = [
        {"column": b64_encode("customer:customer_id"), "$": b64_encode(cust_id)},
        {"column": b64_encode("customer:customer_name"), "$": b64_encode(data.get("customer_name", "Valued Customer"))},
        {"column": b64_encode("customer:account_type"), "$": b64_encode(data.get("account_type", "Savings"))},
        {"column": b64_encode("transaction:transaction_id"), "$": b64_encode(txn_id)},
        {"column": b64_encode("transaction:transaction_type"), "$": b64_encode(txn_type)},
        {"column": b64_encode("transaction:amount"), "$": b64_encode(amt)},
        {"column": b64_encode("transaction:transaction_date"), "$": b64_encode(txn_date)},
        {"column": b64_encode("transaction:transaction_time"), "$": b64_encode(txn_time)},
        {"column": b64_encode("transaction:transaction_status"), "$": b64_encode(data.get("transaction_status", "SUCCESS"))},
        {"column": b64_encode("transaction:description"), "$": b64_encode(data.get("description", "Direct API Submission"))},
        {"column": b64_encode("account:account_id"), "$": b64_encode(data.get("account_id", f"ACC_{cust_id}"))},
        {"column": b64_encode("account:balance_after_transaction"), "$": b64_encode(data.get("balance_after_transaction", amt))},
        {"column": b64_encode("account:sender_account"), "$": b64_encode(data.get("sender_account", f"ACC_{cust_id}"))},
        {"column": b64_encode("account:receiver_account"), "$": b64_encode(data.get("receiver_account", "N/A"))},
        {"column": b64_encode("location:branch"), "$": b64_encode(data.get("branch", "Main Branch"))},
        {"column": b64_encode("location:city"), "$": b64_encode(data.get("city", "Mumbai"))},
        {"column": b64_encode("payment:payment_method"), "$": b64_encode(data.get("payment_method", "UPI"))}
    ]
    
    payload = {"Row": [{"key": b64_encode(row_key), "Cell": cells}]}
    
    try:
        put_res = requests.put(
            f"{HBASE_REST_URL}/bank_transactions/false-row-key",
            data=json.dumps(payload),
            headers=HEADERS,
            timeout=8
        )
        if put_res.status_code in [200, 204]:
            return jsonify({
                "success": True,
                "message": "Transaction inserted successfully into HBase",
                "row_key": row_key,
                "transaction_id": txn_id
            }), 201
        return jsonify({"error": f"HBase returned status {put_res.status_code}: {put_res.text}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/transactions/<path:row_key>", methods=["PUT"])
def update_transaction(row_key):
    """
    CRUD: UPDATE operation.
    Update status, description, or amount for an existing HBase record.
    """
    data = request.json or {}
    cells = []
    if "transaction_status" in data:
        cells.append({"column": b64_encode("transaction:transaction_status"), "$": b64_encode(data["transaction_status"])})
    if "description" in data:
        cells.append({"column": b64_encode("transaction:description"), "$": b64_encode(data["description"])})
    if "balance_after_transaction" in data:
        cells.append({"column": b64_encode("account:balance_after_transaction"), "$": b64_encode(data["balance_after_transaction"])})
        
    if not cells:
        return jsonify({"error": "No update fields provided"}), 400
        
    payload = {"Row": [{"key": b64_encode(row_key), "Cell": cells}]}
    try:
        put_res = requests.put(
            f"{HBASE_REST_URL}/bank_transactions/{row_key}",
            data=json.dumps(payload),
            headers=HEADERS,
            timeout=8
        )
        if put_res.status_code in [200, 204]:
            return jsonify({"success": True, "message": f"Updated row '{row_key}' in HBase"})
        return jsonify({"error": f"HBase update error: {put_res.status_code}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/transactions/<path:row_key>", methods=["DELETE"])
def delete_transaction(row_key):
    """
    CRUD: DELETE operation.
    Delete a transaction row from HBase.
    """
    try:
        del_res = requests.delete(f"{HBASE_REST_URL}/bank_transactions/{row_key}", timeout=8)
        if del_res.status_code in [200, 204]:
            return jsonify({"success": True, "message": f"Deleted row '{row_key}' from HBase"})
        return jsonify({"error": f"HBase deletion returned status {del_res.status_code}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/customer/<customer_id>", methods=["GET"])
def get_customer(customer_id):
    """
    Retrieve customer details and full transaction history from HBase.
    """
    try:
        scanner_spec = {
            "batch": 100,
            "startRow": b64_encode(f"{customer_id}#"),
            "stopRow": b64_encode(f"{customer_id}~")
        }
        res = requests.put(
            f"{HBASE_REST_URL}/bank_transactions/scanner",
            data=json.dumps(scanner_spec),
            headers=HEADERS,
            timeout=5
        )
        txns = []
        if res.status_code in [200, 201]:
            scanner_url = res.headers.get("Location") or f"{HBASE_REST_URL}/bank_transactions/scanner/{res.text.strip()}"
            scan_res = requests.get(scanner_url, headers=HEADERS, timeout=8)
            if scan_res.status_code == 200:
                rows = scan_res.json().get("Row", [])
                txns = [parse_hbase_row(r) for r in rows]
            try:
                requests.delete(scanner_url)
            except Exception:
                pass
                
        # Also check customer_accounts table
        cust_profile = {}
        try:
            acc_res = requests.get(f"{HBASE_REST_URL}/customer_accounts/{customer_id}*", headers=HEADERS, timeout=5)
            if acc_res.status_code == 200:
                acc_rows = acc_res.json().get("Row", [])
                if acc_rows:
                    cust_profile = parse_hbase_row(acc_rows[0])
        except Exception:
            pass

        return jsonify({
            "customer_id": customer_id,
            "profile": cust_profile,
            "total_transactions": len(txns),
            "transactions": txns
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/summary", methods=["GET"])
def get_summary():
    """Return top-level aggregated banking transaction metrics."""
    summary_file = os.path.join(RESULTS_DIR, "transaction_summary.json")
    if os.path.exists(summary_file):
        with open(summary_file, mode="r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    return jsonify({"error": "Summary data not yet computed. Run scripts/analyze_data.py"}), 404

@app.route("/api/suspicious", methods=["GET"])
def get_suspicious():
    """Return rule-based suspicious transactions."""
    suspicious_file = os.path.join(RESULTS_DIR, "suspicious_transactions.json")
    if os.path.exists(suspicious_file):
        with open(suspicious_file, mode="r", encoding="utf-8") as f:
            data = json.load(f)
        limit = int(request.args.get("limit", 100))
        return jsonify({
            "total_suspicious": len(data),
            "records": data[:limit]
        })
    return jsonify({"error": "Suspicious transactions not yet analyzed"}), 404

@app.route("/api/statistics", methods=["GET"])
def get_statistics():
    """Return comprehensive visual statistics for Chart.js dashboards."""
    summary_file = os.path.join(RESULTS_DIR, "transaction_summary.json")
    if os.path.exists(summary_file):
        with open(summary_file, mode="r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({
            "status_distribution": data.get("status_distribution", {}),
            "type_distribution": data.get("type_distribution", {}),
            "payment_method_distribution": data.get("payment_method_distribution", {}),
            "city_distribution": data.get("city_distribution", {}),
            "monthly_summary": data.get("monthly_summary", {}),
            "top_customers": data.get("top_customers_by_volume", [])[:10],
            "deposits_vs_withdrawals": {
                "Deposits": data.get("total_deposits", 0.0),
                "Withdrawals": data.get("total_withdrawals", 0.0),
                "Transfers": data.get("total_transfers", 0.0)
            }
        })
    return jsonify({"error": "Statistics not available"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[INFO] Starting Bank Transaction Backend API on http://localhost:{port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
