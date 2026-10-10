import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { AppLayout } from '../components/layout/AppLayout'
import { Button } from '../components/common/Button'
import { Card, CardContent } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import { Modal } from '../components/common/Modal'
import {
  ShieldCheck,
  Clock,
  HelpCircle,
  CheckCircle2,
  Lock,
  ArrowRight,
  Database,
  Cpu,
  Layers,
} from 'lucide-react'

export const LandingPage: React.FC = () => {
  const [complaintModalOpen, setComplaintModalOpen] = useState(false)

  const steps = [
    {
      num: '01',
      title: 'Submit Dispute',
      description:
        'Customer submits dispute facts with optional order details, serial numbers, and incident documentation.',
      icon: Layers,
    },
    {
      num: '02',
      title: 'AI Policy Investigation',
      description:
        'Deterministic multi-agent nodes query ChromaDB policy vectors, check warranty status, and evaluate return windows.',
      icon: Cpu,
    },
    {
      num: '03',
      title: 'Resolution & Human Approval',
      description:
        'Safe claims are resolved instantly; high-value disputes or exceptions escalate to supervisors with strict SLA tracking.',
      icon: CheckCircle2,
    },
  ]

  const governancePillars = [
    {
      title: 'Tiered Approval Ceilings',
      description:
        'Frontline agents resolve routine claims. Tier-2 Supervisors approve up to ₹25,000. Senior Supervisors manage high-value cases.',
      icon: Lock,
    },
    {
      title: 'Active SLA Countdown',
      description:
        'Every supervisory approval has an enforceable deadline. Overdue items enter jeopardy and require senior override.',
      icon: Clock,
    },
    {
      title: 'Customer Clarification Loop',
      description:
        'Instead of rejecting ambiguous claims, workflows pause and query the customer for missing details before resuming.',
      icon: HelpCircle,
    },
    {
      title: 'Explainable Policy Citations',
      description:
        'Every decision links back to verified ecommerce policy clauses and database facts for complete auditability.',
      icon: Database,
    },
  ]

  return (
    <AppLayout onOpenComplaintModal={() => setComplaintModalOpen(true)}>
      {/* Hero Section */}
      <section className="relative pt-16 pb-20 md:pt-24 md:pb-28 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full">
        <div className="text-center max-w-3xl mx-auto space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-brand-sage/40 bg-brand-sage/10 text-brand-forest dark:text-brand-sage text-xs font-semibold uppercase tracking-wider">
            <ShieldCheck className="w-3.5 h-3.5" />
            Deterministic AI Governance Platform
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-gray-900 dark:text-white leading-[1.15]">
            AI-Powered Complaint Resolution with{' '}
            <span className="text-brand-forest dark:text-brand-sage">
              Human Oversight
            </span>
          </h1>

          <p className="text-base sm:text-lg text-gray-600 dark:text-gray-300 leading-relaxed max-w-2xl mx-auto">
            Resolve ecommerce disputes rapidly with multi-agent policy verification,
            automated investigation, strict approval SLAs, and human supervisor governance.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            <Button
              variant="primary"
              size="lg"
              onClick={() => setComplaintModalOpen(true)}
              className="w-full sm:w-auto font-semibold"
            >
              Submit a Complaint
            </Button>
            <Link to="/login" className="w-full sm:w-auto">
              <Button
                variant="outline"
                size="lg"
                rightIcon={<ArrowRight className="w-4 h-4" />}
                className="w-full sm:w-auto font-semibold"
              >
                Staff Login
              </Button>
            </Link>
          </div>

          <div className="pt-4 flex items-center justify-center gap-6 text-xs text-gray-500 dark:text-gray-400">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" /> LangGraph Orchestrated
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" /> ChromaDB Policy RAG
            </span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" /> RBAC Protected
            </span>
          </div>
        </div>
      </section>

      {/* 3-Step Process Section */}
      <section className="py-16 bg-brand-white dark:bg-dark-card border-y border-gray-200/80 dark:border-dark-border/80 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <Badge variant="neutral" size="sm" className="mb-2">
              Resolution Architecture
            </Badge>
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
              Three-Step Autonomous Resolution
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              From intake to settlement, each stage adheres to verified enterprise guidelines.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {steps.map((step) => {
              const Icon = step.icon
              return (
                <Card key={step.num} variant="default" className="relative group">
                  <CardContent className="p-6 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="w-10 h-10 rounded-lg bg-brand-forest/10 dark:bg-brand-sage/10 text-brand-forest dark:text-brand-sage flex items-center justify-center">
                        <Icon className="w-5 h-5" />
                      </div>
                      <span className="font-mono text-2xl font-bold text-gray-300 dark:text-gray-600">
                        {step.num}
                      </span>
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {step.title}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
                      {step.description}
                    </p>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>
      </section>

      {/* Governance & Human Oversight Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <Badge variant="success" size="sm" dot className="mb-2">
            Enterprise Integrity
          </Badge>
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
            Human Oversight and Strict Governance
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            No unmonitored decisions. High-risk compensation actions require verified supervisory approval.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {governancePillars.map((pillar) => {
            const Icon = pillar.icon
            return (
              <Card key={pillar.title} variant="default">
                <CardContent className="p-5 space-y-3">
                  <div className="w-9 h-9 rounded-lg bg-brand-forest text-white flex items-center justify-center">
                    <Icon className="w-4 h-4" />
                  </div>
                  <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                    {pillar.title}
                  </h3>
                  <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
                    {pillar.description}
                  </p>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </section>

      {/* Complaint Workflow Preview Modal */}
      <Modal
        isOpen={complaintModalOpen}
        onClose={() => setComplaintModalOpen(false)}
        title="Customer Complaint Intake"
        description="Phase 1 Foundation Setup"
        footer={
          <Button variant="primary" size="sm" onClick={() => setComplaintModalOpen(false)}>
            Acknowledge
          </Button>
        }
      >
        <div className="space-y-3">
          <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-300">
            <strong>Frontend Foundation Active:</strong> The customer intake flow will connect directly to <code className="font-mono">POST /api/v1/workflows/resolve</code> during Phase 4 of implementation.
          </div>
          <p className="text-xs text-gray-600 dark:text-gray-300">
            The backend multi-agent complaint resolution workflow is already operational in FastAPI and verified with 195 passing tests.
          </p>
          <div className="border border-gray-200 dark:border-dark-border rounded-lg p-3 space-y-1.5 bg-gray-50 dark:bg-dark-bg text-xs">
            <div className="font-semibold text-gray-700 dark:text-gray-200">
              Supported Complaint Features:
            </div>
            <ul className="list-disc list-inside space-y-0.5 text-gray-500 dark:text-gray-400">
              <li>Automatic Order & Warranty lookup</li>
              <li>Policy retrieval via ChromaDB</li>
              <li>Supervisory approvals for refunds &gt; ₹25,000</li>
              <li>Customer clarification loop for missing facts</li>
            </ul>
          </div>
        </div>
      </Modal>
    </AppLayout>
  )
}
