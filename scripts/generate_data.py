#!/usr/bin/env python3
"""
Bank Transaction System Using Apache HBase with Docker
Script: generate_data.py
Description: Generates realistic banking transaction dataset (10,000+ records)
             with genuine banking distributions, customer accounts, realistic
             balances, and specific fraud/suspicious transaction patterns for analytics.
"""

import os
import csv
import random
from datetime import datetime, timedelta

# Ensure reproducibility while maintaining realistic variety
random.seed(42)

TOTAL_RECORDS = 10500
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "bank_transactions.csv")

# Reference Data
CUSTOMER_POOL = [
    {"id": f"CUST{1000 + i}", "name": name, "city": city, "branch": branch, "acc_type": acc_type}
    for i, (name, city, branch, acc_type) in enumerate([
        ("Aarav Sharma", "Mumbai", "Nariman Point", "Savings"),
        ("Priya Patel", "Mumbai", "Bandra Kurla Complex", "Current"),
        ("Rahul Verma", "Delhi", "Connaught Place", "Salary"),
        ("Ananya Iyer", "Chennai", "Anna Nagar", "Savings"),
        ("Vikram Singh", "Bengaluru", "Whitefield", "Current"),
        ("Sneha Kulkarni", "Pune", "Shivaji Nagar", "Salary"),
        ("Rohan Gupta", "Kolkata", "Salt Lake", "Savings"),
        ("Neha Reddy", "Hyderabad", "Hitec City", "Salary"),
        ("Arjun Nair", "Kochi", "MG Road", "Savings"),
        ("Pooja Joshi", "Ahmedabad", "SG Highway", "Current"),
        ("Siddharth Malhotra", "Mumbai", "Andheri East", "Savings"),
        ("Divya Menon", "Bengaluru", "Indiranagar", "Salary"),
        ("Kavita Rao", "Hyderabad", "Banjara Hills", "Current"),
        ("Aditya Deshmukh", "Pune", "Kothrud", "Savings"),
        ("Meera Sen", "Kolkata", "Park Street", "Salary"),
        ("Manish Tiwari", "Delhi", "Saket", "Current"),
        ("Tanvi Chawla", "Chandigarh", "Sector 17", "Savings"),
        ("Karthik Subramanian", "Chennai", "T Nagar", "Salary"),
        ("Ritu Aggarwal", "Jaipur", "MI Road", "Savings"),
        ("Harsh Vardhan", "Lucknow", "Hazratganj", "Current"),
        ("Ishaan Mukherjee", "Kolkata", "New Town", "Salary"),
        ("Anushka Sengupta", "Mumbai", "Powai", "Savings"),
        ("Nikhil Bhat", "Bengaluru", "Koramangala", "Current"),
        ("Suresh Raina", "Chennai", "Velachery", "Salary"),
        ("Swati Mishra", "Delhi", "Dwarka", "Savings"),
        ("Rajesh Koothrappali", "Delhi", "Hauz Khas", "Current"),
        ("Shreya Ghoshal", "Mumbai", "Juhu", "Salary"),
        ("Gaurav Kapoor", "Delhi", "Rajouri Garden", "Savings"),
        ("Rhea Pillai", "Bengaluru", "Electronic City", "Salary"),
        ("Deepak Chopra", "Pune", "Viman Nagar", "Current"),
        ("Sunita Williams", "Ahmedabad", "Vastrapur", "Savings"),
        ("Abhishek Banerjee", "Kolkata", "Howrah", "Current"),
        ("Gayatri Devi", "Jaipur", "C-Scheme", "Salary"),
        ("Manoj Bajpayee", "Patna", "Boring Road", "Savings"),
        ("Kiran Mazumdar", "Bengaluru", "Hebbal", "Current"),
        ("Varun Dhawan", "Mumbai", "Bandra West", "Salary"),
        ("Preeti Zinta", "Shimla", "Mall Road", "Savings"),
        ("Tarun Tahiliani", "Delhi", "Chanakyapuri", "Current"),
        ("Leela Samson", "Chennai", "Adyar", "Salary"),
        ("Devendra Fadnavis", "Nagpur", "Civil Lines", "Current"),
        ("Sanjay Singhania", "Mumbai", "Worli", "Current"),
        ("Farhan Akhtar", "Mumbai", "Bandra", "Salary"),
        ("Tara Sutaria", "Mumbai", "Colaba", "Savings"),
        ("Pranab Mukherjee", "Kolkata", "Ballygunge", "Current"),
        ("Zoya Akhtar", "Mumbai", "Bandra", "Salary"),
        ("Raghuram Rajan", "Chennai", "Mylapore", "Savings"),
        ("Nandan Nilekani", "Bengaluru", "Jayanagar", "Current"),
        ("Sourav Ganguly", "Kolkata", "Behala", "Savings"),
        ("Sanath Jayasuriya", "Chennai", "Egmore", "Savings"),
        ("Smriti Mandhana", "Mumbai", "Sangli", "Salary")
    ] * 6)  # 300 customers total
]

# Assign account IDs and initial balances
for idx, cust in enumerate(CUSTOMER_POOL):
    cust["account_id"] = f"ACC9000{1000 + idx}"
    # Seed realistic starting balances: ₹25,000 to ₹1,500,000
    cust["current_balance"] = round(random.uniform(25000.0, 1500000.0), 2)

TRANSACTION_TYPES = ["Deposit", "Withdrawal", "Transfer", "Payment", "ATM", "UPI"]
PAYMENT_METHODS = ["UPI", "ATM", "NEFT", "RTGS", "IMPS", "Debit Card", "Credit Card", "Cash"]
TRANSACTION_STATUSES = ["SUCCESS", "SUCCESS", "SUCCESS", "SUCCESS", "SUCCESS", "SUCCESS", "FAILED", "PENDING", "REVERSED"]

METHOD_COMPATIBILITY = {
    "Deposit": ["Cash", "NEFT", "IMPS", "UPI"],
    "Withdrawal": ["ATM", "Cash", "Debit Card"],
    "Transfer": ["NEFT", "RTGS", "IMPS", "UPI"],
    "Payment": ["UPI", "Debit Card", "Credit Card", "NEFT"],
    "ATM": ["ATM", "Debit Card"],
    "UPI": ["UPI"]
}

DESCRIPTIONS = {
    "Deposit": [
        "Salary credited for month",
        "Direct client invoice settlement",
        "Cash deposit at cash deposit machine",
        "Dividend payout credited",
        "Cash deposit via branch counter",
        "Fixed deposit interest payout",
        "Rental income deposit"
    ],
    "Withdrawal": [
        "ATM cash withdrawal",
        "Cheque withdrawal at home branch",
        "Cash withdrawal for personal expenses",
        "Emergency ATM cash withdrawal",
        "Over the counter cash withdrawal"
    ],
    "Transfer": [
        "Fund transfer to vendor account",
        "Inter-bank NEFT transfer to family",
        "Immediate payment transfer via IMPS",
        "High value business settlement via RTGS",
        "Peer-to-peer fund transfer",
        "Monthly rent remittance"
    ],
    "Payment": [
        "E-commerce purchase payment",
        "Utility electricity bill payment",
        "Credit card outstanding payment",
        "Insurance annual premium payment",
        "Supermarket grocery bill payment",
        "Broadband internet bill payment"
    ],
    "ATM": [
        "ATM cash withdrawal - Metro station",
        "ATM cash withdrawal - Shopping mall",
        "ATM cash withdrawal - Airport terminal",
        "ATM cash withdrawal - Branch lobby"
    ],
    "UPI": [
        "UPI payment to grocery store",
        "UPI payment at fuel station",
        "UPI payment for dining out",
        "UPI payment to retail merchant",
        "UPI payment for food delivery",
        "UPI payment for cab ride"
    ]
}

def generate_transactions(total_records=TOTAL_RECORDS):
    print(f"[INFO] Generating {total_records} realistic banking transactions...")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 3, 31)
    date_range_days = (end_date - start_date).days

    transactions = []
    
    # We will introduce realistic suspicious patterns:
    # Pattern 1: High value anomalies (> ₹250,000 to ₹1,000,000)
    # Pattern 2: Bursts / rapid successive transactions for the same account within seconds/minutes
    # Pattern 3: Multiple failed attempts followed by a large transaction
    
    for i in range(1, total_records + 1):
        txn_id = f"TXN{10000000 + i}"
        customer = random.choice(CUSTOMER_POOL)
        
        # Pick transaction date and time
        random_days = random.randint(0, date_range_days)
        txn_datetime = start_date + timedelta(
            days=random_days,
            hours=random.randint(6, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )
        txn_date = txn_datetime.strftime("%Y-%m-%d")
        txn_time = txn_datetime.strftime("%H:%M:%S")
        
        # Determine transaction type and matching payment method
        txn_type = random.choice(TRANSACTION_TYPES)
        payment_method = random.choice(METHOD_COMPATIBILITY[txn_type])
        
        # Calculate realistic amount based on type
        if txn_type == "UPI":
            amount = round(random.uniform(50.0, 15000.0), 2)
        elif txn_type == "ATM":
            amount = round(random.choice([500, 1000, 2000, 3000, 5000, 10000, 15000, 20000]), 2)
        elif txn_type == "Payment":
            amount = round(random.uniform(100.0, 45000.0), 2)
        elif txn_type == "Deposit":
            amount = round(random.uniform(5000.0, 150000.0), 2)
        elif txn_type == "Withdrawal":
            amount = round(random.uniform(1000.0, 50000.0), 2)
        elif txn_type == "Transfer":
            if payment_method == "RTGS":
                # RTGS is strictly for high value transactions >= 200,000
                amount = round(random.uniform(200000.0, 850000.0), 2)
            else:
                amount = round(random.uniform(1000.0, 100000.0), 2)
        
        # Inject occasional suspicious high-amount anomaly (~1.5% of dataset)
        if random.random() < 0.015:
            amount = round(random.uniform(350000.0, 1200000.0), 2)
            txn_type = "Transfer"
            payment_method = "RTGS" if amount >= 200000 else "IMPS"
        
        # Accounts
        sender_account = customer["account_id"]
        if txn_type in ["Transfer", "Payment"]:
            other_cust = random.choice(CUSTOMER_POOL)
            receiver_account = other_cust["account_id"] if other_cust["account_id"] != sender_account else f"ACC9999{random.randint(1000, 9999)}"
        elif txn_type == "Deposit":
            receiver_account = customer["account_id"]
            sender_account = f"EXT9999{random.randint(1000, 9999)}"
        else:
            receiver_account = "N/A"
            
        # Status
        status = random.choice(TRANSACTION_STATUSES)
        
        # Update running balance realistically
        curr_bal = customer["current_balance"]
        if status == "SUCCESS":
            if txn_type in ["Deposit"]:
                curr_bal += amount
            else:
                if curr_bal >= amount:
                    curr_bal -= amount
                else:
                    # Insufficient funds triggers FAILED transaction
                    status = "FAILED"
        elif status == "REVERSED":
            # Reversed transactions don't deduct permanently
            pass

        customer["current_balance"] = round(max(curr_bal, 500.0), 2)
        balance_after = customer["current_balance"]
        
        description = random.choice(DESCRIPTIONS[txn_type])
        
        transactions.append({
            "transaction_id": txn_id,
            "customer_id": customer["id"],
            "account_id": customer["account_id"],
            "customer_name": customer["name"],
            "account_type": customer["acc_type"],
            "transaction_date": txn_date,
            "transaction_time": txn_time,
            "transaction_type": txn_type,
            "amount": amount,
            "balance_after_transaction": balance_after,
            "sender_account": sender_account,
            "receiver_account": receiver_account,
            "branch": customer["branch"],
            "city": customer["city"],
            "payment_method": payment_method,
            "transaction_status": status,
            "description": description
        })

    # Inject Suspicious Rapid Burst Sequences (e.g. 5 transactions in under 2 minutes for same account)
    burst_cust = CUSTOMER_POOL[5]
    burst_date = "2026-02-14"
    for b_idx in range(5):
        burst_txn_id = f"TXN{10000000 + total_records + b_idx + 1}"
        transactions.append({
            "transaction_id": burst_txn_id,
            "customer_id": burst_cust["id"],
            "account_id": burst_cust["account_id"],
            "customer_name": burst_cust["name"],
            "account_type": burst_cust["acc_type"],
            "transaction_date": burst_date,
            "transaction_time": f"02:14:{10 + b_idx * 15:02d}", # rapid within 1 minute at 2 AM
            "transaction_type": "Transfer",
            "amount": 95000.0,
            "balance_after_transaction": round(burst_cust["current_balance"], 2),
            "sender_account": burst_cust["account_id"],
            "receiver_account": f"ACC_MULE_{b_idx + 1}",
            "branch": burst_cust["branch"],
            "city": burst_cust["city"],
            "payment_method": "IMPS",
            "transaction_status": "SUCCESS" if b_idx % 2 == 0 else "FAILED",
            "description": "Rapid successive high velocity transfer"
        })

    # Sort lexicographically by customer_id, date, and time for realistic historical consistency
    transactions.sort(key=lambda x: (x["customer_id"], x["transaction_date"], x["transaction_time"]))

    # Write CSV
    headers = [
        "transaction_id", "customer_id", "account_id", "customer_name",
        "account_type", "transaction_date", "transaction_time",
        "transaction_type", "amount", "balance_after_transaction",
        "sender_account", "receiver_account", "branch", "city",
        "payment_method", "transaction_status", "description"
    ]
    
    with open(OUTPUT_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(transactions)

    print(f"[SUCCESS] Generated {len(transactions)} transaction records.")
    print(f"[SUCCESS] Dataset written to: {OUTPUT_FILE}")
    return len(transactions)

if __name__ == "__main__":
    generate_transactions()
