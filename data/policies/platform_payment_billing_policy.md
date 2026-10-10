---
policy_id: "POL-PLAT-004"
title: "Platform Payment, Billing, and Reconciliation Policy"
version: "1.0.0"
effective_date: "2026-01-01"
scope: "platform"
seller_id: null
category: null
document_type: "policy"
synthetic_policy: true
---

# Platform Payment, Billing, and Reconciliation Policy

> [!NOTE]
> **Synthetic Demonstration Policy**: This document is an artificial e-commerce policy created solely for the ResolveAI autonomous agent system demonstration and automated testing. It does not represent actual legal rules, commercial contracts, or official consumer terms of any company.

---

## 1. Scope & Currency Standards
This policy specifies the operational protocols for transaction processing, billing inquiries, and reconciliation across the ResolveAI marketplace platform. All customer transactions are processed strictly in Indian Rupees (INR) with monetary fields persisted as integer paise to ensure zero floating-point calculation discrepancy.

## 2. Supported Indian Payment Methods
1. **Unified Payments Interface (UPI)**: Instant payments via validated Virtual Payment Addresses (VPAs) across approved PSP apps (BHIM, Google Pay, PhonePe, Paytm).
2. **Debit & Credit Cards**: Domestic RuPay, Visa, and Mastercard cards verified via Reserve Bank of India (RBI) Two-Factor Authentication (OTP / 3D Secure).
3. **NetBanking**: Direct debit from authorized Indian scheduled commercial banks.
4. **Cash on Delivery (COD)**: Payment collected at customer doorstep in legal tender up to a transaction ceiling of ₹50,000.00 (50,00,000 paise).

## 3. Failed, Pending & Duplicate Transactions
1. **Deduction Without Order Placement**: In cases where customer account is debited but network failure prevents order creation:
   - System relies on automated Payment Gateway (PG) webhook reconciliation within 2 hours.
   - If unlinked, funds are auto-reversed by the acquiring bank within 2 to 4 business days under NPCI turnaround norms.
2. **Duplicate Debits**: If a customer experiences multiple debits for a single order identifier:
   - The customer must provide the 12-digit Unique Transaction Reference (UTR) or Bank Reference Number.
   - The secondary duplicate payment is verified with the gateway and scheduled for reversal within 24 hours.
3. **Pending Status**: Orders marked with pending payment verification must not be released for warehouse fulfillment until successful payment webhook confirmation is recorded.

## 4. Refund Reconciliation Constraints
- **Absolute Audit Requirement**: Support agents and autonomous AI agents are strictly prohibited from stating that a refund has been completed or money has been sent unless a verified payment gateway transaction reference exists in database logs.
- **Limitation Notification**: When database records show an internal `approval_requests` entry marked `approved`, agents must explicitly explain: *"An internal approval has been recorded, but external bank disbursement is pending gateway clearing."*

## 5. Worked Examples (INR)
- **Example A**: Customer debited ₹8,999.00 (899900 paise) via UPI VPA for a mechanical keyboard, but checkout timed out. Customer provides 12-digit UTR `428901234567`. Support verifies PG unassigned status and confirms automated bank reversal within 48 hours.
- **Example B**: Customer claims refund of ₹24,999.00 (2499900 paise) was credited. Agent inspects database, verifies internal approval exists without payment gateway disbursement record, and provides factual status update without false completion promises.
