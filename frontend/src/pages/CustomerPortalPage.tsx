import React, { useMemo } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { AppLayout } from '../components/layout/AppLayout'
import { CustomerHero } from '../components/customer/CustomerHero'
import { CustomerComplaintForm } from '../components/customer/CustomerComplaintForm'
import { CustomerCaseTracker } from '../components/customer/CustomerCaseTracker'
import { FileText, Search, Info } from 'lucide-react'

export const CustomerPortalPage: React.FC = () => {
  const { caseId } = useParams<{ caseId?: string }>()
  const location = useLocation()
  const navigate = useNavigate()

  // Derive active tab directly from URL location
  const activeTab: 'overview' | 'complaint' | 'track' = useMemo(() => {
    if (caseId || location.pathname.includes('/track') || location.pathname.includes('/cases')) {
      return 'track'
    }
    if (location.pathname.includes('/complaint')) {
      return 'complaint'
    }
    return 'overview'
  }, [caseId, location.pathname])

  const handleTabChange = (tab: 'overview' | 'complaint' | 'track') => {
    if (tab === 'complaint') {
      navigate('/customer/complaint')
    } else if (tab === 'track') {
      navigate('/customer/track')
    } else {
      navigate('/customer')
    }
  }

  const handleCaseCreated = (newCaseNumber: string) => {
    navigate(`/customer/cases/${newCaseNumber}`)
  }

  return (
    <AppLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Navigation Tabs */}
        <div className="flex border-b border-gray-200 dark:border-dark-border overflow-x-auto">
          <button
            type="button"
            id="tab-customer-overview"
            onClick={() => handleTabChange('overview')}
            className={`flex items-center gap-2 py-3 px-5 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
              activeTab === 'overview'
                ? 'border-brand-forest text-brand-forest dark:border-brand-sage dark:text-brand-sage'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            <Info className="w-4 h-4" />
            <span>Overview & Process</span>
          </button>

          <button
            type="button"
            id="tab-customer-complaint"
            onClick={() => handleTabChange('complaint')}
            className={`flex items-center gap-2 py-3 px-5 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
              activeTab === 'complaint'
                ? 'border-brand-forest text-brand-forest dark:border-brand-sage dark:text-brand-sage'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>File Complaint</span>
          </button>

          <button
            type="button"
            id="tab-customer-track"
            onClick={() => handleTabChange('track')}
            className={`flex items-center gap-2 py-3 px-5 text-sm font-semibold border-b-2 transition-colors whitespace-nowrap ${
              activeTab === 'track'
                ? 'border-brand-forest text-brand-forest dark:border-brand-sage dark:text-brand-sage'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
            }`}
          >
            <Search className="w-4 h-4" />
            <span>Track Existing Case</span>
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <CustomerHero onSelectAction={handleTabChange} />
        )}

        {activeTab === 'complaint' && (
          <div className="max-w-4xl mx-auto">
            <CustomerComplaintForm onCaseCreated={handleCaseCreated} />
          </div>
        )}

        {activeTab === 'track' && (
          <CustomerCaseTracker initialCaseId={caseId} />
        )}
      </div>
    </AppLayout>
  )
}
