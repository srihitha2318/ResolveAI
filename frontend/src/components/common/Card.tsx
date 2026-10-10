import React from 'react'
import { cn } from '../../utils/cn'

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'bordered' | 'elevated'
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ children, className, variant = 'default', ...props }, ref) => {
    const baseStyles =
      'bg-brand-white dark:bg-dark-card rounded-xl transition-colors duration-150'

    const variantStyles = {
      default:
        'border border-gray-200/80 dark:border-dark-border shadow-subtle',
      bordered:
        'border-2 border-gray-300 dark:border-dark-border shadow-none',
      elevated:
        'border border-gray-200/60 dark:border-dark-border shadow-card hover:shadow-elevation transition-shadow',
    }

    return (
      <div
        ref={ref}
        className={cn(baseStyles, variantStyles[variant], className)}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = 'Card'

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div className={cn('p-5 pb-3 border-b border-gray-100 dark:border-dark-border/60', className)} {...props}>
    {children}
  </div>
)

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
  className,
  children,
  ...props
}) => (
  <h3 className={cn('text-lg font-semibold text-gray-900 dark:text-gray-100 tracking-tight', className)} {...props}>
    {children}
  </h3>
)

export const CardDescription: React.FC<React.HTMLAttributes<HTMLParagraphElement>> = ({
  className,
  children,
  ...props
}) => (
  <p className={cn('text-sm text-gray-500 dark:text-gray-400 mt-1', className)} {...props}>
    {children}
  </p>
)

export const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div className={cn('p-5', className)} {...props}>
    {children}
  </div>
)

export const CardFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div className={cn('p-5 pt-3 border-t border-gray-100 dark:border-dark-border/60 flex items-center justify-between', className)} {...props}>
    {children}
  </div>
)
