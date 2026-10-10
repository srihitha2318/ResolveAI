import React from 'react'
import { Button } from '../common/Button'
import { Badge } from '../common/Badge'
import {
  FileText,
  Search,
  ShieldCheck,
  Zap,
  Clock,
  CheckCircle2,
  HelpCircle,
} from 'lucide-react'

interface CustomerHeroProps {
  onSelectAction: (tab: 'complaint' | 'track') => void
}

export const CustomerHero: React.FC<CustomerHeroProps> = ({ onSelectAction }) => {
  return (
    <div className="space-y-12">
      {/* Hero Banner */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-brand-forest via-[#1a5543] to-[#0f3428] text-white p-8 md:p-12 shadow-card">
        {/* Decorative background grid effect */}
        <div className="absolute inset-0 bg-[radial-gradient(#72A58B_1px,transparent_1px)] [background-size:24px_24px] opacity-15 pointer-events-none" />

        <div className="relative z-10 max-w-3xl space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 text-xs font-semibold tracking-wide text-brand-sageLight">
            <Zap className="w-3.5 h-3.5 text-brand-sageLight" />
            <span>AI-Powered Autonomous Customer Support</span>
          </div>

          <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight leading-tight">
            Fair, Instant, & Policy-Verified Resolution.
          </h1>

          <p className="text-base md:text-lg text-gray-200 leading-relaxed max-w-2xl">
            ResolveAI analyzes your complaint against verified marketplace merchant policies
            in real time. Whether your delivery was delayed, damaged, or cancelled, get an
            objective resolution backed by transparent evidence.
          </p>

          <div className="flex flex-wrap gap-4 pt-2">
            <Button
              id="customer-hero-submit-btn"
              variant="secondary"
              size="lg"
              className="bg-white text-brand-forest hover:bg-gray-100 font-semibold shadow-md"
              onClick={() => onSelectAction('complaint')}
              leftIcon={<FileText className="w-4 h-4" />}
            >
              Submit a Complaint
            </Button>
            <Button
              id="customer-hero-track-btn"
              variant="outline"
              size="lg"
              className="border-white/40 text-white hover:bg-white/10 font-semibold"
              onClick={() => onSelectAction('track')}
              leftIcon={<Search className="w-4 h-4" />}
            >
              Track Existing Case
            </Button>
          </div>
        </div>

        {/* Feature stats counter strip */}
        <div className="relative z-10 mt-10 pt-8 border-t border-white/15 grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-white/10 text-brand-sageLight">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xl font-bold text-white">&lt; 30 Seconds</p>
              <p className="text-xs text-gray-300">Average AI Triage Time</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-white/10 text-brand-sageLight">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xl font-bold text-white">100% Policy Grounded</p>
              <p className="text-xs text-gray-300">Verified Against Store Terms</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-white/10 text-brand-sageLight">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xl font-bold text-white">Strict SLA Protection</p>
              <p className="text-xs text-gray-300">Fast Escalation Safeguards</p>
            </div>
          </div>
        </div>
      </section>

      {/* 3-Step Resolution Process */}
      <section className="space-y-6">
        <div className="text-center max-w-xl mx-auto space-y-2">
          <Badge variant="neutral" size="sm" className="font-semibold uppercase tracking-wider">
            Resolution Process
          </Badge>
          <h2 className="text-2xl md:text-3xl font-bold text-gray-900 dark:text-white">
            How ResolveAI Resolves Your Issue
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            A clear, predictable, and fair dispute management workflow from intake to decision.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Step 1 */}
          <div className="relative p-6 rounded-xl bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-subtle hover:shadow-card transition-shadow flex flex-col justify-between">
            <div className="space-y-4">
              <div className="w-10 h-10 rounded-lg bg-brand-forest/10 dark:bg-brand-forest/30 text-brand-forest dark:text-brand-sage flex items-center justify-center font-bold text-base">
                1
              </div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                Intake & Verification
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                Describe your issue and provide your registered order details. Our AI analyzes
                the situation and checks delivery milestones directly against the order records.
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-gray-100 dark:border-dark-border/60 flex items-center gap-1.5 text-xs text-brand-forest dark:text-brand-sage font-medium">
              <CheckCircle2 className="w-4 h-4" />
              <span>Real database verification</span>
            </div>
          </div>

          {/* Step 2 */}
          <div className="relative p-6 rounded-xl bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-subtle hover:shadow-card transition-shadow flex flex-col justify-between">
            <div className="space-y-4">
              <div className="w-10 h-10 rounded-lg bg-brand-sage/20 text-brand-forest dark:text-brand-sage flex items-center justify-center font-bold text-base">
                2
              </div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                Policy Matching & Independent Audit
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                Semantic retrieval finds the specific refund and replacement clauses for your product category.
                An independent Verifier Agent audits the claim to prevent contradictions.
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-gray-100 dark:border-dark-border/60 flex items-center gap-1.5 text-xs text-brand-forest dark:text-brand-sage font-medium">
              <CheckCircle2 className="w-4 h-4" />
              <span>Transparent policy citations</span>
            </div>
          </div>

          {/* Step 3 */}
          <div className="relative p-6 rounded-xl bg-white dark:bg-dark-card border border-gray-200 dark:border-dark-border shadow-subtle hover:shadow-card transition-shadow flex flex-col justify-between">
            <div className="space-y-4">
              <div className="w-10 h-10 rounded-lg bg-brand-forest/10 dark:bg-brand-forest/30 text-brand-forest dark:text-brand-sage flex items-center justify-center font-bold text-base">
                3
              </div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                Resolution or Human Escalation
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                Eligible standard cases receive immediate resolution records. High-value claims or complex edge cases
                are seamlessly escalated to a human supervisor under strict SLA timers.
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-gray-100 dark:border-dark-border/60 flex items-center gap-1.5 text-xs text-brand-forest dark:text-brand-sage font-medium">
              <CheckCircle2 className="w-4 h-4" />
              <span>Escalation with supervisor review</span>
            </div>
          </div>
        </div>
      </section>

      {/* Helpful Support FAQ / Guidance */}
      <section className="p-6 md:p-8 rounded-xl bg-brand-softGray dark:bg-dark-card/60 border border-gray-200/80 dark:border-dark-border space-y-4">
        <div className="flex items-center gap-2">
          <HelpCircle className="w-5 h-5 text-brand-forest dark:text-brand-sage" />
          <h3 className="text-base font-bold text-gray-900 dark:text-white">
            Customer Support Notice & Guidelines
          </h3>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
          ResolveAI creates official internal dispute records, support tickets, and supervisor review approvals.
          ResolveAI does not execute bank transfers or chargebacks directly. Approved resolutions are processed
          through your store's customer billing team according to standard banking cycles.
        </p>
        <div className="flex flex-wrap items-center gap-6 pt-2 text-xs text-gray-500 dark:text-gray-400">
          <span>• Demo Account: alice.chen@example.com (Orders: ORD-2026-001, ORD-2026-002)</span>
          <span>• Demo Account: bob.martinez@example.com (Orders: ORD-2026-003, ORD-2026-004)</span>
        </div>
      </section>
    </div>
  )
}
