import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from '../components/common/Button'
import { Badge } from '../components/common/Badge'
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card'
import { Modal } from '../components/common/Modal'

describe('Reusable Design System Components', () => {
  describe('Button', () => {
    it('renders primary button with text', () => {
      render(<Button variant="primary">Submit</Button>)
      const btn = screen.getByRole('button', { name: /submit/i })
      expect(btn).toBeInTheDocument()
      expect(btn).toHaveClass('bg-brand-forest')
    })

    it('handles click events', () => {
      const handleClick = vi.fn()
      render(<Button onClick={handleClick}>Click Me</Button>)
      fireEvent.click(screen.getByRole('button', { name: /click me/i }))
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('renders disabled and loading states', () => {
      render(
        <Button isLoading disabled>
          Loading Button
        </Button>
      )
      const btn = screen.getByRole('button', { name: /loading button/i })
      expect(btn).toBeDisabled()
      expect(btn).toHaveAttribute('aria-busy', 'true')
    })

    it('applies danger variant classes', () => {
      render(<Button variant="danger">Reject</Button>)
      expect(screen.getByRole('button', { name: /reject/i })).toHaveClass('bg-status-error')
    })
  })

  describe('Badge', () => {
    it('renders semantic variants with accessible content', () => {
      const { rerender } = render(<Badge variant="success">Approved</Badge>)
      expect(screen.getByText('Approved')).toBeInTheDocument()

      rerender(<Badge variant="pending" dot>Pending Review</Badge>)
      expect(screen.getByText('Pending Review')).toBeInTheDocument()

      rerender(<Badge variant="error">Breached SLA</Badge>)
      expect(screen.getByText('Breached SLA')).toBeInTheDocument()
    })
  })

  describe('Card', () => {
    it('renders card with header, title, and content', () => {
      render(
        <Card variant="default">
          <CardHeader>
            <CardTitle>Case Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Case details content</p>
          </CardContent>
        </Card>
      )

      expect(screen.getByText('Case Summary')).toBeInTheDocument()
      expect(screen.getByText('Case details content')).toBeInTheDocument()
    })
  })

  describe('Modal', () => {
    it('renders when isOpen is true and closes on escape key', () => {
      const handleClose = vi.fn()
      render(
        <Modal isOpen={true} onClose={handleClose} title="Complaint Modal">
          <p>Modal content</p>
        </Modal>
      )

      expect(screen.getByText('Complaint Modal')).toBeInTheDocument()
      expect(screen.getByText('Modal content')).toBeInTheDocument()

      fireEvent.keyDown(window, { key: 'Escape' })
      expect(handleClose).toHaveBeenCalledTimes(1)
    })

    it('does not render when isOpen is false', () => {
      render(
        <Modal isOpen={false} onClose={() => {}} title="Hidden Modal">
          <p>Hidden content</p>
        </Modal>
      )

      expect(screen.queryByText('Hidden Modal')).not.toBeInTheDocument()
    })
  })
})
