---
policy_id: "POL-PLAT-007"
title: "Platform Dispute and Delivery Anomaly Review Policy"
version: "1.0.0"
effective_date: "2026-01-01"
scope: "platform"
seller_id: null
category: null
document_type: "policy"
synthetic_policy: true
---

# Platform Dispute and Delivery Anomaly Review Policy

> [!NOTE]
> **Synthetic Demonstration Policy**: This document is an artificial e-commerce policy created solely for the ResolveAI autonomous agent system demonstration and automated testing. It does not represent actual legal rules, commercial contracts, or official consumer terms of any company.

---

## 1. Scope & Core Principle
This policy specifies how anomalous claims, delivery disputes, and evidence discrepancies are evaluated on the ResolveAI marketplace platform.
**Foundational Rule**: Support personnel and autonomous agents must maintain a strict presumption of customer and seller good faith. Accusations of fraud are strictly prohibited; investigations must focus solely on objective factual verification.

## 2. Common Anomaly Categories
1. **Delivery Discrepancies (Delivered vs Received)**:
   - Carrier tracking indicates status `delivered` with or without Proof of Delivery (POD).
   - Customer reports non-receipt of the parcel.
   - Protocol: Carrier hub is tasked to produce the Digital POD containing GPS coordinate timestamp or delivery OTP confirmation.
2. **Weight & Content Discrepancies (Empty Box or Wrong Item Claims)**:
   - Customer claims outer package was delivered empty or contained tiles/soap instead of electronics.
   - Protocol: Cross-reference shipping label gross weight with fulfillment center weigh-scale manifest recorded at dispatch. Discrepancies exceeding 100 grams trigger carrier loss investigation.
3. **Repeated High-Frequency Claims**:
   - Accounts filing more than 3 consecutive defect or damage claims within 30 days are assigned to senior dispute investigators for thorough telemetry inspection.

## 3. Evidence Preservation Protocol
- All customer photographs, unboxing clips, carrier dispatch weight manifests, and delivery executive statements must be preserved in the case documentation record.
- Do not alter or overwrite historical case events during an ongoing investigation.

## 4. Worked Examples (INR)
- **Dispute A**: Customer claims non-receipt of a ₹34,999.00 (3499900 paise) tablet marked delivered. Carrier provides signed POD with mismatched recipient name and no OTP entry. Decision: Carrier claim initiated; provisional replacement recommended for supervisor sign-off.
- **Dispute B**: Customer claims empty box for a ₹1,299.00 (129900 paise) smartwatch. Dispatch weight was 350 grams, while delivery receipt records 340 grams. Decision: Customer is requested to share outer tamper-evident tape photos; matter escalated for hub investigation under Tier 1 guidelines.
