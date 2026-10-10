import React from 'react'
import { Sun, Moon } from 'lucide-react'
import { useTheme } from '../../hooks/useTheme'
import { cn } from '../../utils/cn'

export interface ThemeToggleProps {
  className?: string
  showLabel?: boolean
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ className, showLabel = false }) => {
  const { theme, toggleTheme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={cn(
        'inline-flex items-center gap-2 p-2 rounded-lg text-gray-600 dark:text-gray-300 hover:text-brand-forest dark:hover:text-brand-sage hover:bg-gray-100 dark:hover:bg-dark-cardHover transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-forest dark:focus-visible:ring-brand-sage',
        className
      )}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {isDark ? (
        <Sun className="w-5 h-5 transition-transform duration-200 rotate-0" aria-hidden="true" />
      ) : (
        <Moon className="w-5 h-5 transition-transform duration-200 -rotate-12" aria-hidden="true" />
      )}
      {showLabel && (
        <span className="text-xs font-medium">
          {isDark ? 'Light' : 'Dark'}
        </span>
      )}
    </button>
  )
}
