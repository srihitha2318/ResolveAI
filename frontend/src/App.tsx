import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from './context/ThemeContext'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/layout/ProtectedRoute'
import { LandingPage } from './pages/LandingPage'
import { CustomerPortalPage } from './pages/CustomerPortalPage'
import { LoginPage } from './pages/LoginPage'
import { AgentWorkspacePage } from './pages/AgentWorkspacePage'
import { SupervisorDashboardPage } from './pages/SupervisorDashboardPage'
import { NotFoundPage } from './pages/NotFoundPage'

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />

            {/* Customer Portal Routes */}
            <Route path="/customer" element={<CustomerPortalPage />} />
            <Route path="/customer/complaint" element={<CustomerPortalPage />} />
            <Route path="/customer/track" element={<CustomerPortalPage />} />
            <Route path="/customer/cases/:caseId" element={<CustomerPortalPage />} />
            <Route path="/customer/clarifications" element={<CustomerPortalPage />} />

            {/* Protected Agent Workspace Routes */}
            <Route
              path="/agent"
              element={
                <ProtectedRoute allowedRoles={['frontline_agent', 'tier2_supervisor', 'senior_supervisor']}>
                  <AgentWorkspacePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/app"
              element={
                <ProtectedRoute allowedRoles={['frontline_agent', 'tier2_supervisor', 'senior_supervisor']}>
                  <AgentWorkspacePage />
                </ProtectedRoute>
              }
            />

            {/* Protected Supervisor Routes */}
            <Route
              path="/supervisor"
              element={
                <ProtectedRoute allowedRoles={['tier2_supervisor', 'senior_supervisor']}>
                  <SupervisorDashboardPage />
                </ProtectedRoute>
              }
            />

            {/* 404 Catch-All */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App
