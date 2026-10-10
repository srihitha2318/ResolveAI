---
policy_id: "POL-PLAT-005"
title: "Platform Support Escalation and Human Review Policy"
version: "1.0.0"
effective_date: "2026-01-01"
scope: "platform"
seller_id: null
category: null
document_type: "policy"
synthetic_policy: true
---

# Platform Support Escalation and Human Review Policy

> [!NOTE]
> **Synthetic Demonstration Policy**: This document is an artificial e-commerce policy created solely for the ResolveAI autonomous agent system demonstration and automated testing. It does not represent actual legal rules, commercial contracts, or official consumer terms of any company.

---

## 1. Purpose & Authority Structure
This policy establishes unambiguous routing criteria for escalating customer support cases from frontline autonomous agents to human supervisors and specialized operational desks.

## 2. Mandatory Escalation Triggers
A support case must immediately transition to `escalated` status with an assigned supervisor under any of the following conditions:
1. **High Monetary Value**: Any resolution recommendation involving goods, refunds, or replacements with order total exceeding **₹25,000.00 (25,00,000 paise)**.
2. **Standard Threshold Excess**: Any proposed financial exception exceeding the Tier 1 threshold of **₹5,000.00 (5,00,000 paise)**.
3. **Policy Precedence Conflicts**: Situations where seller-specific conditions contradict platform return or consumer safety mandates.
4. **Repeated Carrier Delivery Failures**: Shipments with 2 or more unsuccessful delivery attempts (NDR - Non-Delivery Report) due to address confusion or courier delay exceeding 5 business days past expected date.
5. **Conflicting Factual Evidence**: Inconsistencies between customer physical damage claims and carrier delivery weight telemetry or dispatch imaging.
6. **Suspected Security or Account Anomalies**: Multiple simultaneous refund claims across different accounts originating from identical device footprints.

## 3. Human Approval Process & Logging
1. **Creation of Approval Record**: When an escalation condition is met, the system creates a formal entry in `approval_requests` with `requested_action`, `status='pending'`, and detailed factual `justification`.
2. **Review SLA**: Tier 2 supervisors must review pending approvals within 4 business hours.
3. **Decision Audit**: The supervisor must record an explicit `decision_reason` whether approved or rejected.
4. **Event Trail**: An atomic entry is written to `case_events` logging the approval transition.

## 4. Rejection Handling Protocol
If a supervisor rejects an approval request:
- The case status returns to `in_progress`.
- The customer must receive an objective explanation of missing requirements or policy limitations.
- Agents must offer viable alternatives (e.g., manufacturer warranty referral or authorized repair center evaluation) rather than leaving the customer unassisted.

## 5. Worked Examples (INR)
- **Case 1**: A customer requests replacement for a damaged 65-inch Smart TV valued at ₹74,990.00 (7499000 paise). Because value exceeds ₹25,000.00, frontline agents must not auto-approve; case is routed to supervisor queue with serial number audit.
- **Case 2**: Seller Deccan Digital states electronics must be returned within 5 days, while Platform Return Policy mandates 7 days. Because platform rule takes precedence, case is flagged for supervisor review to align seller fulfillment.
