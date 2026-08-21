/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./templates/**/*.html', './static/**/*.js'],
  safelist: ['collapsed', 'expanded'],
  theme: {
    extend: {
      colors: {
        primary: '#4361ee',
        'primary-dark': '#3f37c9',
        'primary-darker': '#3730a3',
        'gradient-start': '#4e54c8',
        'gradient-end': '#8f94fb',
        positive: '#28a745',
        negative: '#dc3545',
        // NOTE: this shadows Tailwind's built-in neutral-50..950 grayscale palette by design — used for sentiment badges (bg-neutral/text-neutral), not the gray scale.
        neutral: '#ffc107',
        surface: '#ffffff',
        'app-bg': '#f8f9fa',
        'text-dark': '#333333',
        'text-medium': '#555555',
        'text-muted': '#6c757d',
        'border-light': '#e2e8f0',
        'border-lighter': '#e9ecef',
        'footer-dark': '#2c2f49',
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
        navbar: '0 0.15rem 1.75rem 0 rgba(63, 55, 201, 0.15)',
        'card-base': '0 15px 30px rgba(0, 0, 0, 0.1)',
        'card-hover': '0 20px 40px rgba(0, 0, 0, 0.15)',
        'input-focus': '0 0 0 0.25rem rgba(67, 97, 238, 0.25)',
        'button-primary': '0 4px 15px rgba(78, 84, 200, 0.4)',
        'button-primary-hover': '0 7px 20px rgba(63, 55, 201, 0.6)',
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg, #4e54c8 0%, #8f94fb 100%)',
        'brand-gradient-h': 'linear-gradient(90deg, #4e54c8 0%, #8f94fb 100%)',
        'brand-gradient-h-hover': 'linear-gradient(90deg, #3730a3 0%, #3f37c9 100%)',
      },
      fontFamily: {
        sans: ['Poppins', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
