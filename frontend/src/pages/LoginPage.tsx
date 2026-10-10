import React, { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { AppLayout } from '../components/layout/AppLayout'
import { Button } from '../components/common/Button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import { ShieldCheck, User, Key, ArrowLeft, AlertCircle } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { ApiError } from '../types/api'

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated, user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Redirect if already authenticated
  React.useEffect(() => {
    if (isAuthenticated && user) {
      if (user.role === 'tier2_supervisor' || user.role === 'senior_supervisor') {
        navigate('/supervisor', { replace: true })
      } else {
        navigate('/agent', { replace: true })
      }
    }
  }, [isAuthenticated, user, navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)

    const cleanUsername = username.trim()
    const cleanPassword = password.trim()

    if (!cleanUsername) {
      setErrorMsg('Please enter your staff username.')
      return
    }

    if (!cleanPassword) {
      setErrorMsg('Please enter your account password.')
      return
    }

    setIsSubmitting(true)
    try {
      const loggedUser = await login({ username: cleanUsername, password: cleanPassword })

      // Determine destination
      const fromPath = (location.state as { from?: { pathname?: string } })?.from?.pathname
      if (fromPath && fromPath !== '/login') {
        navigate(fromPath, { replace: true })
      } else if (loggedUser.role === 'tier2_supervisor' || loggedUser.role === 'senior_supervisor') {
        navigate('/supervisor', { replace: true })
      } else {
        navigate('/agent', { replace: true })
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setErrorMsg('Invalid username or password. Please verify your credentials.')
        } else if (err.status === 0) {
          setErrorMsg('Unable to connect to the authentication service. Please ensure the backend is running.')
        } else {
          setErrorMsg(err.message || 'Authentication failed. Please try again.')
        }
      } else {
        setErrorMsg('An unexpected error occurred during login. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AppLayout>
      <div className="flex-1 flex items-center justify-center p-4 sm:p-6 my-8">
        <div className="w-full max-w-md space-y-6">
          {/* Back Navigation */}
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-brand-forest dark:hover:text-brand-sage transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Public Portal
          </Link>

          {/* Login Card */}
          <Card variant="default">
            <CardHeader className="text-center pb-4">
              <div className="mx-auto w-12 h-12 rounded-xl bg-brand-forest flex items-center justify-center shadow-subtle mb-3">
                <ShieldCheck className="w-6 h-6 text-white" />
              </div>
              <CardTitle className="text-xl">Staff Authentication Gateway</CardTitle>
              <CardDescription>
                Internal portal for Frontline Support and Supervisory Command
              </CardDescription>
            </CardHeader>

            <form onSubmit={handleSubmit}>
              <CardContent className="space-y-4">
                {/* Error Banner */}
                {errorMsg && (
                  <div
                    className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-800 dark:text-rose-300 flex items-start gap-2 animate-in fade-in"
                    role="alert"
                  >
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{errorMsg}</span>
                  </div>
                )}

                {/* Form Fields */}
                <div className="space-y-3">
                  <div>
                    <label
                      htmlFor="username"
                      className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1"
                    >
                      Staff Username
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                        <User className="w-4 h-4" />
                      </div>
                      <input
                        id="username"
                        name="username"
                        type="text"
                        autoComplete="username"
                        autoFocus
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="e.g. supervisor_alice"
                        className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-gray-300 dark:border-dark-border bg-brand-white dark:bg-dark-bg text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-forest dark:focus:ring-brand-sage transition-all"
                      />
                    </div>
                  </div>

                  <div>
                    <label
                      htmlFor="password"
                      className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1"
                    >
                      Account Password
                    </label>
                    <div className="relative">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                        <Key className="w-4 h-4" />
                      </div>
                      <input
                        id="password"
                        name="password"
                        type="password"
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Enter your password"
                        className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-gray-300 dark:border-dark-border bg-brand-white dark:bg-dark-bg text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-forest dark:focus:ring-brand-sage transition-all"
                      />
                    </div>
                  </div>
                </div>

                {/* Reference Accounts Note */}
                <div className="pt-2 border-t border-gray-100 dark:border-dark-border/60 space-y-1.5">
                  <span className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider block">
                    Supported Role Profiles
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    <Badge variant="neutral" size="sm" title="Routine intake & triage">
                      frontline_agent
                    </Badge>
                    <Badge variant="pending" size="sm" title="Approvals up to ₹25,000">
                      tier2_supervisor
                    </Badge>
                    <Badge variant="success" size="sm" title="High-value & SLA overrides">
                      senior_supervisor
                    </Badge>
                  </div>
                  <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1">
                    Demo reference handles in database: <code>supervisor_alice</code>, <code>senior_bob</code>, <code>agent_charlie</code>.
                  </p>
                </div>
              </CardContent>

              <CardFooter className="flex-col gap-2.5">
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  isLoading={isSubmitting}
                  className="w-full font-semibold"
                >
                  Sign In to Workspace
                </Button>
                <p className="text-[11px] text-gray-400 dark:text-gray-500 text-center">
                  Protected with HMAC-SHA256 Bearer Token
                </p>
              </CardFooter>
            </form>
          </Card>
        </div>
      </div>
    </AppLayout>
  )
}
