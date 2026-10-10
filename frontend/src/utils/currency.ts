/**
 * Utility functions for Indian Rupee (INR ₹) formatting
 */

export function formatINR(amountPaiseOrRupees: number | null | undefined, isPaise = false): string {
  if (amountPaiseOrRupees === null || amountPaiseOrRupees === undefined || isNaN(amountPaiseOrRupees)) {
    return '₹0.00'
  }

  const rupees = isPaise ? amountPaiseOrRupees / 100 : amountPaiseOrRupees
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(rupees)
}

export function formatPaiseToINR(paise: number | null | undefined): string {
  return formatINR(paise, true)
}
