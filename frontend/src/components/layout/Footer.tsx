import React, { useEffect, useState } from 'react'
import { getSystemStatus } from '../../services/api'
import type { SystemStatusResponse } from '../../types/api'
import { ShieldCheck, Server } from 'lucide-react'

const CURRENT_YEAR = new Date().getFullYear()

export const Footer: React.FC = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatusResponse | null>(null)
  const [isOnline, setIsOnline] = useState<boolean | null>(null)

  useEffect(() => {
    let isMounted = true
    const checkStatus = async () => {
      try {
        const data = await getSystemStatus()
        if (isMounted) {
          setSystemStatus(data)
          setIsOnline(data.database === 'connected')
        }
      } catch {
        if (isMounted) {
          setIsOnline(false)
        }
      }
    }

    checkStatus()
    return () => {
      isMounted = false
    }
  }, [])

  return (
    <footer className="w-full border-t border-gray-200/80 dark:border-dark-border/80 bg-brand-white dark:bg-dark-bg transition-colors mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Brand & Mission */}
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-md bg-brand-forest flex items-center justify-center">
              <span className="text-white font-bold text-[10px]">R-AI</span>
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900 dark:text-white">
                Resolve<span className="text-brand-sage">AI</span> Platform
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Deterministic policy verification & human-in-the-loop oversight
              </p>
            </div>
          </div>

          {/* Subsystem status pill */}
          <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-gray-200 dark:border-dark-border bg-gray-50 dark:bg-dark-card">
              <span
                className={`w-2 h-2 rounded-full ${
                  isOnline === true
                    ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse'
                    : isOnline === false
                    ? 'bg-amber-500'
                    : 'bg-gray-400'
                }`}
                aria-hidden="true"
              />
              <span className="font-medium text-gray-700 dark:text-gray-300">
                {isOnline === true
                  ? `Backend ${systemStatus?.version || 'v0.1.0'} Online (${systemStatus?.database || 'connected'})`
                  : isOnline === false
                  ? 'Backend Standby'
                  : 'Probing Subsystems...'}
              </span>
            </div>

            <div className="hidden sm:flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-brand-forest dark:text-brand-sage" />
              <span>SLA Protected</span>
            </div>

            <div className="hidden sm:flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-brand-forest dark:text-brand-sage" />
              <span>FastAPI Proxy</span>
            </div>
          </div>

          {/* Copyright */}
          <div className="text-xs text-gray-400 dark:text-gray-500">
            &copy; {CURRENT_YEAR} ResolveAI. Enterprise Governance Engine.
          </div>
        </div>
      </div>
    </footer>
  )
}
