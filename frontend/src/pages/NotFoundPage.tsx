import React from 'react'
import { Link } from 'react-router-dom'
import { AppLayout } from '../components/layout/AppLayout'
import { Button } from '../components/common/Button'
import { ArrowLeft, FileQuestion } from 'lucide-react'

export const NotFoundPage: React.FC = () => {
  return (
    <AppLayout>
      <div className="flex-1 flex items-center justify-center p-4 sm:p-6 text-center my-12">
        <div className="max-w-md space-y-6">
          <div className="w-16 h-16 rounded-2xl bg-brand-forest/10 dark:bg-brand-sage/10 text-brand-forest dark:text-brand-sage flex items-center justify-center mx-auto">
            <FileQuestion className="w-8 h-8" />
          </div>

          <div className="space-y-2">
            <span className="text-xs font-mono font-bold text-brand-forest dark:text-brand-sage uppercase tracking-wider">
              Error 404
            </span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 dark:text-white tracking-tight">
              Page Not Found
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              The requested operational resource or portal page does not exist or has been relocated.
            </p>
          </div>

          <div>
            <Link to="/">
              <Button
                variant="primary"
                size="md"
                leftIcon={<ArrowLeft className="w-4 h-4" />}
                className="font-semibold"
              >
                Return to Home
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
