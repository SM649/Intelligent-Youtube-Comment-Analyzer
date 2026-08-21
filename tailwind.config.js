/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./templates/**/*.html'],
  safelist: ['clay-blob'],
  theme: {
    extend: {
      colors: {
        primary: 'rgb(var(--clay-blue-rgb) / <alpha-value>)',
        'primary-dark': 'rgb(var(--clay-blue-rgb) / <alpha-value>)',
        positive: 'rgb(var(--clay-blue-rgb) / <alpha-value>)',
        negative: 'rgb(var(--clay-coral-rgb) / <alpha-value>)',
        // NOTE: this shadows Tailwind's built-in neutral-50..950 grayscale palette by design — used for sentiment badges (bg-neutral/text-neutral), not the gray scale.
        neutral: 'rgb(var(--clay-neutral-rgb) / <alpha-value>)',
        surface: 'var(--clay-surface)',
        'app-bg': 'var(--clay-base)',
        'text-dark': 'var(--clay-text)',
        'text-muted': 'var(--clay-muted)',
        'border-light': 'var(--clay-border)',
        'border-lighter': 'var(--clay-border)',
        'footer-dark': 'var(--clay-footer)',
        'sidebar-bg': 'var(--clay-sidebar-bg)',
      },
      spacing: {
        sidebar: '280px',
      },
      borderRadius: {
        'brand-sm': '8px',
        'brand-md': '15px',
        'brand-lg': '30px',
      },
      boxShadow: {
        navbar: '0 8px 20px var(--clay-shadow-dark), 0 -2px 6px var(--clay-shadow-light)',
        'card-base': '6px 6px 14px var(--clay-shadow-dark), -6px -6px 14px var(--clay-shadow-light)',
        'card-hover': '8px 8px 18px var(--clay-shadow-dark), -8px -8px 18px var(--clay-shadow-light)',
        'button-primary': '6px 6px 14px var(--clay-shadow-dark), -4px -4px 10px var(--clay-shadow-light)',
        'button-primary-hover': '8px 8px 18px var(--clay-shadow-dark), -6px -6px 14px var(--clay-shadow-light)',
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg, var(--clay-coral) 0%, var(--clay-coral) 100%)',
      },
      fontFamily: {
        sans: ['Poppins', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
