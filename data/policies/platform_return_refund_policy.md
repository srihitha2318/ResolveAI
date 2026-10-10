---
policy_id: "POL-PLAT-002"
title: "Platform Return and Refund Policy"
version: "1.0.0"
effective_date: "2026-01-01"
scope: "platform"
seller_id: null
category: null
document_type: "policy"
synthetic_policy: true
---

# Platform Return and Refund Policy

> [!NOTE]
> **Synthetic Demonstration Policy**: This document is an artificial e-commerce policy created solely for the ResolveAI autonomous agent system demonstration and automated testing. It does not represent actual legal rules, commercial contracts, or official consumer terms of any company.

---

## 1. Policy Overview
This is the canonical Return and Refund Policy for the ResolveAI marketplace platform. It governs all customer return eligibility evaluations, replacement authorizations, and refund assessments across all participating sellers and product categories. All monetary evaluations are denominated in Indian Rupees (INR) and calculated using integer paise.

## 2. Standard Return Windows
- **Platform General Return Window**: Up to 30 calendar days from the date of confirmed delivery as recorded in the `delivered_at` database timestamp.
- **Category Specific Windows**:
  - *Electronics & Mobiles*: 7 calendar days from confirmed delivery (replacement-first for hardware defects; technician inspection required).
  - *Fashion & Apparel*: 14 calendar days from confirmed delivery (returns or size exchanges accepted with tags and hygiene seals intact).
  - *Home Appliances*: 10 calendar days from confirmed delivery (replacement-first upon on-site technician inspection).
  - *General Merchandise*: 30 calendar days from confirmed delivery.

## 3. Product Condition & Verification Requirements
1. **Physical Integrity**: Items returned must include original brand packaging, intact manufacturer seals, tags, accessories, user manuals, warranty cards, and the platform tax invoice.
2. **Defect Verification**: For damaged, defective, or missing item claims, customer-submitted photos or video unboxing evidence must be uploaded and verified before return pickup is generated.
3. **Serial Number Match**: High-value electronics must match the serial number or IMEI captured at seller dispatch.

## 4. Refund Methods and Processing Rules
1. **Source Account Reimbursement**: Verified refunds are credited exclusively to the original payment instrument (UPI Virtual Payment Address, NetBanking account, or Debit/Credit Card).
2. **Cash on Delivery (COD)**: Orders delivered via COD are reimbursed via direct NEFT/IMPS transfer to verified customer bank account details or platform wallet credit upon customer request.
3. **No Execution Guarantee**: Automated support tools and AI agents evaluate *eligibility only*. No automated agent has authority to execute a banking transfer or claim money was returned without verified payment gateway reconciliation logs.
4. **Processing Expectation**: Once an authorized item is received at the seller return fulfillment center and passes physical inspection, financial reconciliation takes 5 to 7 business days.

## 5. Monetary Thresholds & Approval Tiers
All evaluations operate on integer paise:
- **Tier 1 (Up to ₹5,000.00 / 5,00,000 paise)**: Automated agent assessment is authorized to recommend return or replacement for validated defect evidence.
- **Tier 2 (Exceeding ₹5,000.00 / 5,00,000 paise)**: Requires explicit supervisor review and logged `approval_requests` entry before return authorization.
- **High-Value Cap (Exceeding ₹25,000.00 / 25,00,000 paise)**: Requires supervisor and logistics claims officer co-authorization following serial number and transit telemetry verification.

## 6. Non-Refundable & Excluded Items
The following items are non-returnable unless arrived damaged in transit:
1. Innerwear, lingerie, swimwear, and personal hygiene products once the protective hygiene strip is removed.
2. Consumable items (food, groceries, vitamins) if the outer container seal is opened.
3. Customized or personalized goods tailored specifically to customer specifications.
4. Software, digital codes, or electronics exhibiting signs of unauthorized firmware tampering or physical abuse.

## 7. Worked Examples (INR)
- **Example 1**: Customer requests return of a ₹1,499.00 (149900 paise) cotton shirt 5 days post-delivery due to incorrect size. Tags are intact. Result: *Eligible* under Fashion Policy (within 14 days); Tier 1 auto-approval.
- **Example 2**: Customer requests refund for a ₹18,999.00 (1899900 paise) microwave oven 4 days post-delivery stating non-functional magnetron. Result: *Needs Review*; Home Appliance policy requires technician visit; amount exceeds ₹5,000.00 requiring Tier 2 approval.
- **Example 3**: Customer requests return of shoes 40 days post-delivery. Result: *Ineligible*; exceeds standard return window.
