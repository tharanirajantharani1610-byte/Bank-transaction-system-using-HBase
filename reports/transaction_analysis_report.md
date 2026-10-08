# Banking Transaction Analysis & Fraud Detection Report
*Generated on: 2026-10-08 09:44:11*
*Database Engine: Apache HBase on Docker*

## 1. Executive Summary
- **Total Transactions Analyzed:** 10,505
- **Total Financial Volume:** ₹631,425,036.56
- **Average Transaction Value:** ₹60,107.10
- **Highest Transaction:** ₹1,187,745.97
- **Identified Suspicious Records:** 572

## 2. Transaction Status Distribution
| Status | Transaction Count | Percentage |
| :--- | :--- | :--- |
| SUCCESS | 6,523 | 62.09% |
| FAILED | 1,638 | 15.59% |
| PENDING | 1,165 | 11.09% |
| REVERSED | 1,158 | 11.02% |

## 3. Financial Breakdown by Transaction Type
| Transaction Type | Count | Total Volume (₹) |
| :--- | :--- | :--- |
| Transfer | 1,810 | ₹390,892,607.06 |
| UPI | 1,731 | ₹12,925,751.42 |
| ATM | 1,775 | ₹12,769,000.00 |
| Payment | 1,760 | ₹39,107,677.44 |
| Deposit | 1,654 | ₹126,889,956.55 |
| Withdrawal | 1,712 | ₹43,385,181.10 |
| Unknown | 63 | ₹5,454,862.99 |

## 4. Top Customers by Transaction Volume
| Customer | Total Transactions |
| :--- | :--- |
| Unknown (Unknown) | 147 |
| CUST1031 (Abhishek Banerjee) | 54 |
| CUST1047 (Sourav Ganguly) | 53 |
| CUST1172 (Nikhil Bhat) | 49 |
| CUST1247 (Sourav Ganguly) | 47 |
| CUST1076 (Shreya Ghoshal) | 46 |
| CUST1204 (Vikram Singh) | 46 |
| CUST1243 (Pranab Mukherjee) | 46 |
| CUST1261 (Divya Menon) | 46 |
| CUST1251 (Priya Patel) | 45 |

## 5. Rule-Based Suspicious Activity Detection (Academic Demonstration)
> **Disclaimer:** This detection module utilizes rule-based heuristics designed for educational and academic big-data project evaluation.

Total flagged items: **572**

### Top Flagged Cases
| Transaction ID | Customer | Amount (₹) | Type | Primary Flags |
| :--- | :--- | :--- | :--- | :--- |
| TXN10008236 | Aarav Sharma | ₹453,732.94 | Transfer | High-Value Anomaly (Amount: ₹453,732.94 exceeds threshold ₹300,000) |
| TXN10009007 | Aarav Sharma | ₹362,015.81 | Transfer | High-Value Anomaly (Amount: ₹362,015.81 exceeds threshold ₹300,000) |
| TXN10008150 | Shreya Ghoshal | ₹707,997.45 | Transfer | High-Value Anomaly (Amount: ₹707,997.45 exceeds threshold ₹300,000) |
| TXN10008078 | Sanjay Singhania | ₹10,000.00 | ATM | High Velocity Burst (Executed within 66s of prior transaction) |
| TXN10007513 | Smriti Mandhana | ₹371,653.30 | Transfer | High-Value Anomaly (Amount: ₹371,653.30 exceeds threshold ₹300,000) |
| TXN10007265 | Gaurav Kapoor | ₹369,955.82 | Transfer | High-Value Anomaly (Amount: ₹369,955.82 exceeds threshold ₹300,000) |
| TXN10006229 | None | ₹800,588.65 | Transfer | High-Value Anomaly (Amount: ₹800,588.65 exceeds threshold ₹300,000) |
| TXN10010152 | None | ₹559,548.57 | Transfer | High-Value Anomaly (Amount: ₹559,548.57 exceeds threshold ₹300,000); High-Value Failed Transfer (Possible unauthorized attempt of ₹559,548.57) |
| TXN10005743 | Neha Reddy | ₹401,962.38 | Transfer | High-Value Anomaly (Amount: ₹401,962.38 exceeds threshold ₹300,000); High-Value Failed Transfer (Possible unauthorized attempt of ₹401,962.38) |
| TXN10004063 | Priya Patel | ₹383,234.34 | Transfer | High-Value Anomaly (Amount: ₹383,234.34 exceeds threshold ₹300,000) |
| TXN10009466 | Priya Patel | ₹378,514.31 | Transfer | High-Value Anomaly (Amount: ₹378,514.31 exceeds threshold ₹300,000) |
| TXN10007649 | Priya Patel | ₹201,453.93 | Transfer | High-Value Failed Transfer (Possible unauthorized attempt of ₹201,453.93) |
| TXN10004967 | Rahul Verma | ₹616,915.35 | Transfer | High-Value Anomaly (Amount: ₹616,915.35 exceeds threshold ₹300,000) |
| TXN10002871 | Ananya Iyer | ₹437,356.29 | Transfer | High-Value Anomaly (Amount: ₹437,356.29 exceeds threshold ₹300,000) |
| TXN10000271 | Ananya Iyer | ₹908,708.27 | Transfer | High-Value Anomaly (Amount: ₹908,708.27 exceeds threshold ₹300,000); High-Value Failed Transfer (Possible unauthorized attempt of ₹908,708.27) |
