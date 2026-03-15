/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg:       'var(--bg)',
        surface:  'var(--surface)',
        surface2: 'var(--surface2)',
        border:   'var(--border)',
        border2:  'var(--border2)',
        text:     'var(--text)',
        muted:    'var(--muted)',
        subtle:   'var(--subtle)',
        accent:   'var(--accent)',
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
      },
      borderColor: {
        DEFAULT: 'var(--border)',
      },
      ringColor: {
        DEFAULT: 'var(--accent)',
      },
    },
  },
  plugins: [],
}
