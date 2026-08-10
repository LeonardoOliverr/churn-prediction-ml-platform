/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    container: {
      center: true,
      padding: '1.5rem',
      screens: { '2xl': '1400px' },
    },
    extend: {
      fontFamily: {
        sans:  ['"Inter Tight"', 'Inter', 'system-ui', 'sans-serif'],
        mono:  ['"JetBrains Mono"', '"Fira Code"', 'ui-monospace', 'monospace'],
        metric:['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        /* shadcn primitives — point to OKLCH vars directly */
        border:     'var(--border-1)',
        input:      'var(--bg-inset)',
        ring:       'var(--accent)',
        background: 'var(--bg-1)',
        foreground: 'var(--fg-1)',
        primary: {
          DEFAULT:    'var(--accent)',
          foreground: 'var(--fg-1)',
        },
        secondary: {
          DEFAULT:    'var(--bg-3)',
          foreground: 'var(--fg-2)',
        },
        destructive: {
          DEFAULT:    'var(--crit)',
          foreground: 'var(--fg-1)',
        },
        muted: {
          DEFAULT:    'var(--bg-3)',
          foreground: 'var(--fg-3)',
        },
        /* shadcn "accent" = bg-3 surface (not petroleum blue) */
        accent: {
          DEFAULT:    'var(--bg-3)',
          foreground: 'var(--fg-1)',
        },
        popover: {
          DEFAULT:    'var(--bg-2)',
          foreground: 'var(--fg-1)',
        },
        card: {
          DEFAULT:    'var(--bg-2)',
          foreground: 'var(--fg-1)',
        },
        /* Design token surfaces */
        'bg-0': 'var(--bg-0)',
        'bg-1': 'var(--bg-1)',
        'bg-2': 'var(--bg-2)',
        'bg-3': 'var(--bg-3)',
        'bg-4': 'var(--bg-4)',
        'bg-inset': 'var(--bg-inset)',
        /* Foreground scale */
        'fg-1': 'var(--fg-1)',
        'fg-2': 'var(--fg-2)',
        'fg-3': 'var(--fg-3)',
        'fg-4': 'var(--fg-4)',
        'fg-5': 'var(--fg-5)',
        /* Semantic */
        ok:          'var(--ok)',
        'ok-fg':     'var(--ok-fg)',
        'ok-soft':   'var(--ok-soft)',
        'ok-line':   'var(--ok-line)',
        warn:        'var(--warn)',
        'warn-fg':   'var(--warn-fg)',
        'warn-soft': 'var(--warn-soft)',
        'warn-line': 'var(--warn-line)',
        crit:        'var(--crit)',
        'crit-fg':   'var(--crit-fg)',
        'crit-soft': 'var(--crit-soft)',
        'crit-line': 'var(--crit-line)',
        /* Petroleum accent */
        'accent-hx':   'var(--accent)',
        'accent-fg':   'var(--accent-fg)',
        'accent-soft': 'var(--accent-soft)',
        'accent-line': 'var(--accent-line)',
      },
      borderRadius: {
        '1':  'var(--r-1)',
        '2':  'var(--r-2)',
        '3':  'var(--r-3)',
        sm:   'var(--r-1)',
        md:   'var(--r-2)',
        lg:   'var(--r-3)',
        xl:   '10px',
        '2xl':'14px',
        full: '9999px',
      },
      boxShadow: {
        pop: 'var(--shadow-pop)',
      },
      spacing: {
        sidebar: 'var(--sidebar-w)',
        topbar:  'var(--topbar-h)',
      },
      height: {
        row: 'var(--row-h)',
      },
    },
  },
  plugins: [],
}
