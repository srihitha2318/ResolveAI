---
policy_id: "POL-PLAT-003"
title: "Platform Order Cancellation Policy"
version: "1.0.0"
effective_date: "2026-01-01"
scope: "platform"
seller_id: null
category: null
document_type: "policy"
synthetic_policy: true
---

# Platform Order Cancellation Policy

> [!NOTE]
> **Synthetic Demonstration Policy**: This document is an artificial e-commerce policy created solely for the ResolveAI autonomous agent system demonstration and automated testing. It does not represent actual legal rules, commercial contracts, or official consumer terms of any company.

---

## 1. Scope & Principles
This policy sets forth the synthetic rules governing customer-initiated and seller-initiated order cancellations across the ResolveAI marketplace platform for orders denominated in Indian Rupees (INR).

## 2. Cancellation Stages & Eligibility
1. **Prior to Seller Order Acceptance**: Customers may cancel any order instantaneously via self-service portal or customer support. Zero cancellation charges apply. Full payment authorization is immediately released or refunded.
2. **Prior to Dispatch (Order Processing)**: If the seller has confirmed the order but logistics carrier pickup has not occurred (`order_status: processing`, `delivery_status: not_shipped`), customer cancellation is guaranteed with 100% refund.
3. **Post-Dispatch (In Transit)**: Once the shipment has been picked up by the logistics carrier (`delivery_status: in_transit` or `delayed`), direct cancellation is halted in the database. Instead:
   - The platform sends an automated Return-to-Origin (RTO) recall instruction to the carrier hub.
   - The customer is advised to decline delivery upon doorstep arrival by delivery executive.
   - Financial refund is scheduled upon confirmation of parcel return tracking.
4. **Post-Delivery**: Once an order has been marked `delivered`, cancellation is closed; any customer dispute must proceed under the [Platform Return and Refund Policy](platform_return_refund_policy.md).

## 3. Cancellation Charges & Fees
- Standard consumer products (electronics, apparel, home appliances, general merchandise) carry **zero cancellation charges** at all pre-dispatch stages.
- Customized, engraved, or tailor-made merchandise is non-cancellable once manufacturing has commenced.

## 4. Refund Timeline Post-Cancellation
- **UPI Transactions**: Reversal initiated within 24 to 48 hours directly to the paying VPA.
- **Credit / Debit Cards**: Refund processed within 3 to 5 banking days, subject to card issuer clearing.
- **NetBanking & Wallets**: Credited within 2 to 4 business days.

## 5. Worked Examples (INR)
- **Example A**: Customer cancels a ₹3,999.00 (399900 paise) smartwatch order 2 hours after placement while status is `processing`. Cancellation is approved automatically; 100% refund of ₹3,999.00 scheduled.
- **Example B**: Customer requests cancellation for a ₹54,990.00 (5499000 paise) refrigerator currently in transit (`delivery_status: in_transit`). Agent instructs carrier for RTO and advises customer to decline delivery at doorstep.
