/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        verdict: {
          pass: '#0F7B3C',
          review: '#B75B00',
          violation: '#B3261E',
          insufficient: '#5B5F66',
        },
      },
    },
  },
  plugins: [],
}

