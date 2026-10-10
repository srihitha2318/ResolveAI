---
policy_id: "POL-PLAT-008"
title: "Platform Shipping, Delivery, and Logistics Policy"
version: "1.0.0"
effective_date: "2026-01-01"
scope: "platform"
seller_id: null
category: null
document_type: "policy"
synthetic_policy: true
---

# Platform Shipping, Delivery, and Logistics Policy

> [!NOTE]
> **Synthetic Demonstration Policy**: This document is an artificial e-commerce policy created solely for the ResolveAI autonomous agent system demonstration and automated testing. It does not represent actual legal rules, commercial contracts, or official consumer terms of any company.

---

## 1. Delivery Timelines Across Indian Pincodes
1. **Tier 1 Metro Zones (Delhi NCR, Mumbai, Bengaluru, Hyderabad, Chennai, Kolkata, Pune, Ahmedabad)**:
   - Standard delivery: 2 to 4 business days from order confirmation.
   - Express priority shipping: 1 to 2 business days.
2. **Tier 2 & Tier 3 Regional Centers**:
   - Standard delivery: 4 to 7 business days from order confirmation.
3. **Special & Remote Logistics Sectors (Northeast states, Jammu & Kashmir, Island territories)**:
   - Standard delivery: 7 to 10 business days via India Post / Surface Air Cargo.

## 2. Delayed Delivery Protocols
1. **Delayed Classification**: An order is formally classified as `delayed` when tracking indicates the parcel has not arrived within **2 business days** following the stored `expected_delivery_date`.
2. **Carrier Status Inquiry**:
   - Frontline support agents immediately trigger an automated logistics hub trace with partner carriers (e.g. BlueDart, Delhivery, Ekart, India Post).
   - If tracking has remained static or inactive at an intermediate hub for **5 consecutive business days**, an internal transit investigation is lodged.

## 3. High-Value Secure OTP Delivery
- For all high-value shipments exceeding **₹25,000.00 (25,00,000 paise)**, delivery executives are mandated to capture a 4-digit One-Time Password (OTP) sent to the customer's registered mobile number prior to handing over the package.
- Deliveries completed without OTP verification for orders over ₹25,000.00 are non-binding in case of customer non-receipt claims.

## 4. Lost in Transit & Transit Damage Settlements
1. **Confirmed Lost in Transit**:
   - If carrier telemetry confirms a shipment is lost or untraceable for **7 consecutive business days**, the customer is eligible for immediate priority replacement or full refund in Indian Rupees (INR).
2. **Non-Delivery Report (NDR) Management**:
   - If delivery fails due to customer unavailable or door locked, 3 consecutive delivery attempts are made before initiating Return to Origin (RTO).

## 5. Worked Examples (INR)
- **Scenario A**: An order of ₹14,999.00 (1499900 paise) to Jaipur (pincode 302001) has an expected delivery date of 15th September. On 18th September (3 days overdue), status is `delayed`. Agent issues carrier inquiry ticket under Section 2 without requiring human supervisor escalation.
- **Scenario B**: A smartphone valued at ₹49,990.00 (4999000 paise) is delivered without mobile OTP entry, and customer reports non-receipt. Platform logistics audit is initiated; customer is protected under high-value delivery policy Section 3.
