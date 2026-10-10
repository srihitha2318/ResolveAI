import React, { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ThemeToggle } from '../common/ThemeToggle'
import { Button } from '../common/Button'
import { Badge } from '../common/Badge'
import { Menu, X, ArrowUpRight, LogOut, User as UserIcon } from 'lucide-react'
import { cn } from '../../utils/cn'
import { useAuth } from '../../hooks/useAuth'

export interface HeaderProps {
  onOpenComplaintModal?: () => void
}

export const Header: React.FC<HeaderProps> = ({ onOpenComplaintModal }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const { user, isAuthenticated, logout } = useAuth()

  const isSupervisor =
    user?.role === 'tier2_supervisor' || user?.role === 'senior_supervisor'

  const navLinks = [
    { label: 'Overview', href: '/' },
    { label: 'Customer Portal', href: '/customer' },
    ...(isSupervisor ? [{ label: 'Supervisor Command', href: '/supervisor' }] : []),
    { label: 'Agent Workspace', href: '/agent' },
    ...(!isAuthenticated ? [{ label: 'Staff Login', href: '/login' }] : []),
  ]

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-40 w-full bg-brand-white/90 dark:bg-dark-bg/90 backdrop-blur-md border-b border-gray-200/80 dark:border-dark-border/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo */}
          <Link
            to="/"
            className="flex items-center gap-3 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-forest rounded-lg"
          >
            {/* Geometric R-AI Badge */}
            <div className="w-9 h-9 rounded-lg bg-brand-forest flex items-center justify-center shadow-subtle group-hover:bg-brand-forestDark transition-colors">
              <span className="text-white font-extrabold text-xs tracking-tight">R-AI</span>
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-lg tracking-tight text-gray-900 dark:text-white">
                Resolve<span className="text-brand-sage">AI</span>
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                to={link.href}
                className={cn(
                  'px-3.5 py-1.5 rounded-lg text-sm font-medium transition-colors',
                  isActive(link.href)
                    ? 'text-brand-forest dark:text-brand-sage bg-brand-forest/5 dark:bg-brand-sage/10 font-semibold'
                    : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-dark-cardHover'
                )}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* Right actions */}
          <div className="hidden sm:flex items-center gap-3">
            <ThemeToggle />

            {/* Authenticated User Status or Guest Links */}
            {isAuthenticated && user ? (
              <div className="flex items-center gap-3 pl-2 border-l border-gray-200 dark:border-dark-border">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-brand-forest/10 dark:bg-brand-sage/10 text-brand-forest dark:text-brand-sage flex items-center justify-center font-bold text-xs">
                    <UserIcon className="w-4 h-4" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-xs font-semibold text-gray-900 dark:text-white leading-tight">
                      {user.full_name || user.username}
                    </span>
                    <span className="text-[10px] font-mono font-medium text-gray-500 dark:text-gray-400">
                      {user.role}
                    </span>
                  </div>
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  leftIcon={<LogOut className="w-3.5 h-3.5" />}
                  onClick={handleLogout}
                  className="text-xs text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30"
                  title="Sign out"
                >
                  Sign Out
                </Button>
              </div>
            ) : (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onOpenComplaintModal}
                  className="text-xs font-semibold"
                >
                  Submit Complaint
                </Button>
                <Link to="/login">
                  <Button
                    variant="primary"
                    size="sm"
                    rightIcon={<ArrowUpRight className="w-3.5 h-3.5" />}
                    className="text-xs font-semibold"
                  >
                    Staff Portal
                  </Button>
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="flex items-center gap-2 sm:hidden">
            <ThemeToggle />
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-dark-cardHover"
              aria-label="Toggle navigation menu"
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu dropdown */}
      {mobileMenuOpen && (
        <div className="sm:hidden border-b border-gray-200 dark:border-dark-border bg-brand-white dark:bg-dark-card px-4 pt-2 pb-4 space-y-2">
          {isAuthenticated && user && (
            <div className="pb-2 border-b border-gray-100 dark:border-dark-border/60 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-gray-900 dark:text-white block">
                  {user.full_name || user.username}
                </span>
                <span className="text-[10px] text-gray-500 font-mono">{user.role}</span>
              </div>
              <Badge variant="success" size="sm" dot>Active</Badge>
            </div>
          )}

          {navLinks.map((link) => (
            <Link
              key={link.href}
              to={link.href}
              onClick={() => setMobileMenuOpen(false)}
              className={cn(
                'block px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive(link.href)
                  ? 'text-brand-forest dark:text-brand-sage bg-brand-forest/5 dark:bg-brand-sage/10 font-semibold'
                  : 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-dark-cardHover'
              )}
            >
              {link.label}
            </Link>
          ))}

          <div className="pt-2 flex flex-col gap-2">
            {isAuthenticated ? (
              <Button
                variant="danger"
                size="sm"
                leftIcon={<LogOut className="w-3.5 h-3.5" />}
                onClick={() => {
                  setMobileMenuOpen(false)
                  handleLogout()
                }}
                className="w-full justify-center"
              >
                Sign Out
              </Button>
            ) : (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full justify-center"
                  onClick={() => {
                    setMobileMenuOpen(false)
                    onOpenComplaintModal?.()
                  }}
                >
                  Submit Complaint
                </Button>
                <Link to="/login" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="primary" size="sm" className="w-full justify-center">
                    Staff Portal
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  )
}
