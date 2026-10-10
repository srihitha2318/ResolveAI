import React from 'react'
import { Navigate, useLocation, Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import type { UserRole } from '../../types/auth'
import { ShieldAlert, ArrowLeft } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../common/Card'
import { Button } from '../common/Button'

export interface ProtectedRouteProps {
  children: React.ReactNode
  allowedRoles?: UserRole[]
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  allowedRoles,
}) => {
  const { isAuthenticated, isLoading, user } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center p-6 space-y-4">
        <div className="w-10 h-10 rounded-full border-3 border-brand-forest/20 border-t-brand-forest animate-spin" />
        <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">
          Validating authorization session...
        </p>
      </div>
    )
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (allowedRoles && allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center p-4 sm:p-6">
        <Card variant="default" className="max-w-md w-full border-status-error/30 shadow-subtle">
          <CardHeader className="text-center pb-2">
            <div className="mx-auto w-12 h-12 rounded-xl bg-status-errorBg text-status-error flex items-center justify-center mb-2">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <CardTitle className="text-lg">Access Denied</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-center text-xs text-gray-600 dark:text-gray-300">
            <p>
              Your account role (<code className="font-mono font-bold text-gray-800 dark:text-gray-200">{user.role}</code>)
              does not have permission to access this operational console.
            </p>
            <div className="p-3 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border text-[11px] text-gray-500 dark:text-gray-400">
              Required role(s):{' '}
              <span className="font-mono font-semibold text-gray-700 dark:text-gray-300">
                {allowedRoles.join(' or ')}
              </span>
            </div>
            <div className="pt-2">
              <Link to="/app">
                <Button
                  variant="outline"
                  size="sm"
                  leftIcon={<ArrowLeft className="w-3.5 h-3.5" />}
                  className="font-semibold"
                >
                  Return to Workspace Shell
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return <>{children}</>
}
