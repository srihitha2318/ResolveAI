import React from 'react'
import { Header } from '../components/layout/Header'
import { Sidebar } from '../components/layout/Sidebar'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import { Button } from '../components/common/Button'
import { Link } from 'react-router-dom'
import { CheckCircle, AlertTriangle, Clock, Shield } from 'lucide-react'

export const AppShellPage: React.FC = () => {
  return (
    <div className="min-h-screen flex flex-col bg-brand-softgray dark:bg-dark-bg text-gray-900 dark:text-gray-100 transition-colors">
      <Header />

      <div className="flex-1 flex overflow-hidden">
        {/* Workspace Sidebar */}
        <Sidebar className="hidden lg:flex" />

        {/* Main Operational Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
          {/* Top Operational Banner */}
          <div className="p-4 rounded-xl bg-brand-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-subtle flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-brand-forest/10 dark:bg-brand-sage/10 text-brand-forest dark:text-brand-sage flex items-center justify-center shrink-0">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-base font-bold text-gray-900 dark:text-white">
                  Operational Application Shell
                </h1>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Previewing ResolveAI workspace layout and persona modules
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="pending" size="sm" dot>
                Foundation Mode
              </Badge>
              <Link to="/login">
                <Button variant="outline" size="sm" className="text-xs">
                  Staff Login Gateway
                </Button>
              </Link>
            </div>
          </div>

          {/* Module Architecture Overview */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Customer Portal Card */}
            <Card variant="default">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <Badge variant="neutral" size="sm">Persona 1</Badge>
                  <span className="text-[11px] font-mono text-gray-400">/customer</span>
                </div>
                <CardTitle className="text-base mt-2">Customer Experience</CardTitle>
                <CardDescription>
                  Public dispute intake, order fact verification, and clarification responses.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs text-gray-600 dark:text-gray-300">
                <div className="space-y-1.5 font-mono text-[11px] text-gray-500 dark:text-gray-400">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                    <span>POST /v1/workflows/resolve</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                    <span>POST /v1/workflows/.../provide-info</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                    <span>GET /v1/cases/:case_number</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Support Agent Card */}
            <Card variant="default">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <Badge variant="neutral" size="sm">Persona 2</Badge>
                  <span className="text-[11px] font-mono text-gray-400">/agent</span>
                </div>
                <CardTitle className="text-base mt-2">Agent Workspace</CardTitle>
                <CardDescription>
                  Frontline support case triage, AI policy reasoning preview, and ticket creation.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs text-gray-600 dark:text-gray-300">
                <div className="space-y-1.5 font-mono text-[11px] text-gray-500 dark:text-gray-400">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                    <span>POST /v1/cases/:id/tickets</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                    <span>POST /v1/cases/:id/events</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                    <span>POST /v1/analyze-complaint</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Supervisor Command Card */}
            <Card variant="default">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <Badge variant="neutral" size="sm">Persona 3</Badge>
                  <span className="text-[11px] font-mono text-gray-400">/supervisor</span>
                </div>
                <CardTitle className="text-base mt-2">Supervisor Command</CardTitle>
                <CardDescription>
                  SLA tracking matrix, high-value approval cards, and senior override actions.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-xs text-gray-600 dark:text-gray-300">
                <div className="space-y-1.5 font-mono text-[11px] text-gray-500 dark:text-gray-400">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                    <span>GET /v1/workflows/pending-approvals</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                    <span>POST /v1/workflows/.../approve</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                    <span>POST /v1/workflows/.../reject</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* SLA Governance Status Preview */}
          <Card variant="default">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base">Approval SLA Matrix (Demonstration Shell)</CardTitle>
                  <CardDescription>
                    Real-time supervisory countdown system conforming to Level 6.2 governance
                  </CardDescription>
                </div>
                <Badge variant="success" size="sm" dot>
                  Rules Active
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-4 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border">
                  <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span>Tier-2 Authority</span>
                    <Clock className="w-3.5 h-3.5 text-brand-forest dark:text-brand-sage" />
                  </div>
                  <div className="text-xl font-bold font-mono text-gray-900 dark:text-white mt-1">
                    ≤ ₹25,000
                  </div>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">
                    Standard 4-hour SLA window
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border">
                  <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span>Senior Authority</span>
                    <Shield className="w-3.5 h-3.5 text-brand-forest dark:text-brand-sage" />
                  </div>
                  <div className="text-xl font-bold font-mono text-gray-900 dark:text-white mt-1">
                    Unlimited
                  </div>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">
                    Authorizes expired SLA overrides
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border">
                  <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span>Clarification Ceiling</span>
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                  </div>
                  <div className="text-xl font-bold font-mono text-gray-900 dark:text-white mt-1">
                    3 Attempts
                  </div>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">
                    Auto-escalates upon exhaustion
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
