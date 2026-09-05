import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        gov: {
          navy: {
            950: '#061324',
            900: '#0B2545',
            800: '#133E6E',
            700: '#1D4E89',
            600: '#2A69AC',
            100: '#E6EFF8',
            50: '#F0F6FC',
          },
          slate: {
            900: '#0F172A',
            800: '#1E293B',
            700: '#334155',
            600: '#475569',
            500: '#64748B',
            400: '#94A3B8',
            300: '#CBD5E1',
            200: '#E2E8F0',
            100: '#F1F5F9',
            50: '#F8FAFC',
          },
        },
        verdict: {
          pass: {
            bg: '#ECFDF5',
            border: '#059669',
            text: '#065F46',
            badge: '#047857',
            icon: '#047857',
          },
          review: {
            bg: '#FFFBEB',
            border: '#D97706',
            text: '#92400E',
            badge: '#B45309',
            icon: '#B45309',
          },
          violation: {
            bg: '#FEF2F2',
            border: '#DC2626',
            text: '#991B1B',
            badge: '#B91C1C',
            icon: '#B91C1C',
          },
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
        mono: [
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'Liberation Mono',
          'Courier New',
          'monospace',
        ],
      },
    },
  },
  plugins: [],
};

export default config;
