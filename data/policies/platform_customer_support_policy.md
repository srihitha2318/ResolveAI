---
policy_id: "POL-PLAT-001"
title: "Platform Customer Support Policy"
version: "1.0.0"
effective_date: "2026-01-01"
scope: "platform"
seller_id: null
category: null
document_type: "policy"
synthetic_policy: true
---

# Platform Customer Support Policy

> [!NOTE]
> **Synthetic Demonstration Policy**: This document is an artificial e-commerce policy created solely for the ResolveAI autonomous agent system demonstration and automated testing. It does not represent actual legal rules, commercial contracts, or official consumer terms of any company.

---

## 1. Policy Overview & Scope
This policy governs customer complaint intake, identification, verification, and lifecycle management across the ResolveAI marketplace platform for transactions conducted in Indian Rupees (INR). It establishes mandatory operating procedures for frontline agents, automated triage pipelines, and human supervisors.

## 2. Complaint Intake & Case Identification
1. **Intake Channels**: Complaints may be submitted via web portal, registered email, or verified mobile messaging.
2. **Mandatory Case Assignment**: Every unique customer inquiry generates a system-assigned Case Identifier (`CASE-YYYY-XXXX`) and an indexed support ticket (`TCK-ID-XXXX`).
3. **Identity Verification**: To safeguard customer privacy, support actions require verification of either the registered phone number, verified email address, or registered order number.
4. **Order Linking**: If a complaint references an order, the case must be formally associated with the unique platform Order Identifier (`ORD-YYYY-XXX`).

## 3. Evidence Gathering & Required Facts
Before any resolution recommendation can be reviewed or actioned:
- **Customer Stored Facts**: Registered name, delivery address, pin code, and order payment status must be retrieved from the persistent database.
- **Order Audit Trail**: The support agent must inspect the stored `order_status`, `delivery_status`, integer monetary value in paise (e.g., ₹1,499.00 = 149900 paise), and confirmed `delivered_at` timestamp.
- **Physical Defect Evidence**: For damaged, broken, or incorrect items, customer-uploaded photographic evidence of the item, shipping label, and unboxing packaging is mandatory before replacement authorization.

## 4. Case Ownership & Status Transitions
Support cases transition through standard deterministic lifecycle states:
- `open`: Newly created inquiry awaiting fact investigation.
- `in_progress`: Active inquiry under verification with seller or logistics carrier.
- `resolved`: Proposed remedy confirmed, documented in `resolution_summary`, and accepted by policy rules.
- `closed`: Customer feedback recorded or 7 business days elapsed post-resolution without dispute.
- `escalated`: Case assigned to Tier 2 supervisor queue due to high value, policy conflict, or repeated delivery failure.

Each status transition must atomically write an audit record to the `case_events` table documenting the timestamp, previous state, and reason.

## 5. Decision Rules & Tiered Authority
- **Tier 1 Automated Assessment**: Automated triage agents may assess claims and recommend standard remedies for orders up to ₹5,000.00 (5,00,000 paise).
- **Tier 2 Supervisor Review**: Mandatory human supervisor review is required if:
  1. The order amount exceeds ₹5,000.00 (5,00,000 paise).
  2. The claim involves high-value electronics exceeding ₹25,000.00 (25,00,000 paise).
  3. The customer has filed more than 3 distinct damage complaints within the preceding 90 days.
  4. Available policy evidence presents an unresolved conflict between seller-specific terms and platform rules.

## 6. Exceptions & Non-Standard Scenarios
- If an order number provided by the customer does not exist in the database, the agent must halt automated remedies, prompt the customer for verified details, and mark the case as requiring additional information.
- No monetary refund or physical replacement may ever be promised or reported as completed without verified backend confirmation.

## 7. Worked Examples (INR)
- **Scenario A**: Customer files inquiry regarding delayed delivery of a ₹2,499.00 (249900 paise) fashion order. Status is `in_progress`; agent checks carrier hub tracking without requiring supervisor escalation.
- **Scenario B**: Customer reports transit damage on a ₹49,990.00 (4999000 paise) smartphone. Because the amount exceeds ₹25,000.00, Tier 2 supervisor approval is flagged mandatory prior to replacement dispatch.
