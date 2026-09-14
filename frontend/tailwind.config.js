/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // DLU Pine/Forest Green - primary brand
        pine: {
          50: '#f0f7f3',
          100: '#dcefe3',
          200: '#b9dfc8',
          300: '#8bc7a6',
          400: '#57a87e',
          500: '#348a5f',
          600: '#226d48',   // primary
          700: '#1b573b',
          800: '#174531',
          900: '#133828',
          950: '#0a1f17',
        },
        // DLU Earthy Brown/Wood - accents & secondary borders
        wood: {
          50: '#faf6f1',
          100: '#f1e7dc',
          200: '#e2cdb7',
          300: '#d0ab88',
          400: '#bd865c',
          500: '#ad6c3f',   // accent
          600: '#a05b33',
          700: '#854a2c',
          800: '#6b3d27',
          900: '#593422',
          950: '#301911',
        },
        // Frosted glass surfaces (deep frosted glass over dark overlay)
        glass: {
          light: 'rgba(255,255,255,0.18)',
          medium: 'rgba(255,255,255,0.25)',
          strong: 'rgba(255,255,255,0.34)',
          dark: 'rgba(255,255,255,0.45)',
          border: 'rgba(255,255,255,0.35)',
          borderStrong: 'rgba(255,255,255,0.45)',
        },
        // Text - pure white, high contrast on dark glass over dark overlay
        ink: {
          primary: '#ffffff',
          secondary: '#f1f5f9',
          tertiary: '#cbd5e1',
          onlight: '#1e293b',
        },
        semantic: {
          success: '#4ade80',
          warning: '#fbbf24',
          error: '#f87171',
        },
        category: {
          word: '#93c5fd',
          excel: '#86efac',
          powerpoint: '#fca5a5',
        }
      },
      fontFamily: {
        sans: ['"Switzer"', '"SF Pro Display"', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        display: ['"Cabinet Grotesk"', '"SF Pro Display"', '"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'card': '16px',
        'panel': '24px',
        'pill': '9999px',
      },
      boxShadow: {
        'glow-soft': '0 8px 32px rgba(16,44,32,0.12)',
        'glow': '0 10px 40px -8px rgba(52,138,95,0.45)',
        'glow-wood': '0 10px 40px -8px rgba(173,108,63,0.45)',
        'glass': '0 8px 32px 0 rgba(13,40,28,0.18)',
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s cubic-bezier(0.16,1,0.3,1)',
        'slide-up': 'slideUp 0.5s cubic-bezier(0.16,1,0.3,1)',
        'slide-up-slow': 'slideUp 0.7s cubic-bezier(0.16,1,0.3,1)',
        'pulse-soft': 'pulseSoft 2.2s ease-in-out infinite',
        'spin-slow': 'spin 1s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(24px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
      },
    },
  },
  plugins: [],
}
