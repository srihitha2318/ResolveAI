import React from 'react'
import { Header } from './Header'
import { Footer } from './Footer'

export interface AppLayoutProps {
  children: React.ReactNode
  onOpenComplaintModal?: () => void
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  children,
  onOpenComplaintModal,
}) => {
  return (
    <div className="min-h-screen flex flex-col bg-brand-softgray dark:bg-dark-bg text-gray-900 dark:text-gray-100 transition-colors">
      <Header onOpenComplaintModal={onOpenComplaintModal} />
      <main className="flex-1 flex flex-col">{children}</main>
      <Footer />
    </div>
  )
}
