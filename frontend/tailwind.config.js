/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg:        '#0A0A0A',
        card:      '#1A1A2E',
        sidebar:   '#111111',
        purple:    '#552583',
        gold:      '#FDB927',
        'text-primary':   '#FFFFFF',
        'text-secondary': '#A0A0B0',
        border:    '#2A2A3E',
        danger:    '#E53935',
        warning:   '#FFB300',
        success:   '#43A047',
        'chip-active':   '#FDB927',
        'chip-inactive': '#2A2A3E',
      },
    },
  },
  plugins: [],
}
