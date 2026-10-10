import { Link, useLocation } from 'react-router-dom'
import {
  FileText,
  Search,
  CheckCircle,
  Clock,
  ShieldAlert,
  UserCheck,
  FolderGit2,
  HelpCircle,
} from 'lucide-react'
import { cn } from '../../utils/cn'
import { useAuth } from '../../hooks/useAuth'

export interface SidebarProps {
  className?: string
}

export const Sidebar: React.FC<SidebarProps> = ({ className }) => {
  const location = useLocation()
  const { user } = useAuth()

  const isSupervisor =
    user?.role === 'tier2_supervisor' || user?.role === 'senior_supervisor'

  const navSections = [
    {
      title: 'Supervisor Command',
      items: [
        {
          label: 'Pending Approvals',
          href: '/supervisor',
          icon: CheckCircle,
          previewOnly: !isSupervisor,
        },
        {
          label: 'SLA Monitoring',
          href: '/supervisor',
          icon: Clock,
          previewOnly: !isSupervisor,
        },
        {
          label: 'Audit Trail & Analytics',
          href: '/supervisor',
          icon: ShieldAlert,
          previewOnly: !isSupervisor,
        },
      ],
    },
    {
      title: 'Frontline Support',
      items: [
        { label: 'Agent Workspace', href: '/agent', icon: FolderGit2, previewOnly: false },
        { label: 'Policy Investigation', href: '/agent', icon: UserCheck, previewOnly: false },
      ],
    },
    {
      title: 'Customer Experience',
      items: [
        { label: 'Submit Complaint', href: '/customer/complaint', icon: FileText, previewOnly: false },
        { label: 'Track Resolution', href: '/customer/track', icon: Search, previewOnly: false },
        { label: 'Clarification Loop', href: '/customer/track', icon: HelpCircle, previewOnly: false },
      ],
    },
  ]

  return (
    <aside
      className={cn(
        'w-64 shrink-0 bg-brand-white dark:bg-dark-card border-r border-gray-200 dark:border-dark-border p-4 flex flex-col gap-6',
        className
      )}
    >
      <div className="flex items-center gap-2.5 px-2">
        <div className="w-8 h-8 rounded-lg bg-brand-forest flex items-center justify-center">
          <span className="text-white font-bold text-xs">R-AI</span>
        </div>
        <div>
          <h2 className="text-sm font-bold text-gray-900 dark:text-white leading-tight">
            Workspace Hub
          </h2>
          <span className="text-[11px] text-gray-500 dark:text-gray-400 font-mono">
            {user ? `${user.role}` : 'Foundation Mode'}
          </span>
        </div>
      </div>

      <nav className="flex-1 space-y-5">
        {navSections.map((section) => (
          <div key={section.title} className="space-y-1">
            <h3 className="px-2.5 text-[11px] font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
              {section.title}
            </h3>
            {section.items.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href

              if (item.previewOnly) {
                return (
                  <div
                    key={item.label}
                    className="flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium text-gray-500 dark:text-gray-400"
                  >
                    <div className="flex items-center gap-2">
                      <Icon className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                      <span>{item.label}</span>
                    </div>
                    <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-gray-100 dark:bg-dark-bg text-gray-400 dark:text-gray-500 font-mono">
                      Phase 3+
                    </span>
                  </div>
                )
              }

              return (
                <Link
                  key={item.label}
                  to={item.href}
                  className={cn(
                    'flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors',
                    isActive
                      ? 'bg-brand-forest/10 text-brand-forest dark:text-brand-sage dark:bg-brand-sage/10 font-bold'
                      : 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-dark-cardHover'
                  )}
                >
                  <div className="flex items-center gap-2">
                    <Icon className="w-4 h-4 text-brand-forest dark:text-brand-sage" />
                    <span>{item.label}</span>
                  </div>
                  <span className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 font-mono font-bold">
                    Active
                  </span>
                </Link>
              )
            })}
          </div>
        ))}
      </nav>

      <div className="p-3 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-dark-border text-xs text-gray-500 dark:text-gray-400">
        <p className="font-semibold text-gray-800 dark:text-gray-200 mb-0.5">
          Level 6 Security Active
        </p>
        <p className="text-[11px] leading-relaxed">
          HMAC-SHA256 authenticated sessions with tiered supervisor approval limits and SLA enforcement.
        </p>
      </div>
    </aside>
  )
}
