/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          forest: '#174C3C',
          forestDark: '#0F3328',
          forestLight: '#1E634F',
          sage: '#72A58B',
          sageDark: '#5B8771',
          sageLight: '#8FBCA4',
          softgray: '#F3F6F4',
          white: '#FFFFFF',
        },
        dark: {
          bg: '#0B1511',
          card: '#13251E',
          cardHover: '#182E25',
          border: '#1F3A2F',
          borderSubtle: '#183027',
          textMuted: '#94A3B8',
        },
        status: {
          success: '#10B981',
          successBg: 'rgba(16, 185, 129, 0.12)',
          warning: '#F59E0B',
          warningBg: 'rgba(245, 158, 11, 0.12)',
          error: '#EF4444',
          errorBg: 'rgba(239, 68, 68, 0.12)',
          neutral: '#6B7280',
          neutralBg: 'rgba(107, 114, 128, 0.12)',
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        subtle: '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)',
        card: '0 4px 6px -1px rgba(0, 0, 0, 0.04), 0 2px 4px -2px rgba(0, 0, 0, 0.04)',
        elevation: '0 10px 15px -3px rgba(0, 0, 0, 0.06), 0 4px 6px -4px rgba(0, 0, 0, 0.04)',
      }
    },
  },
  plugins: [],
}
