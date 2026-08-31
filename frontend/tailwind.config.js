/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // DLU Academic palette - Editorial Luxury + Soft Structuralism
        canvas: {
          50: '#F7F6F3',   // primary warm off-white
          100: '#FBFBFA',
          200: '#EFEEE9',
          300: '#E3E1DA',
        },
        // Deep academic teal - primary brand
        brand: {
          50: '#ECF7F5',
          100: '#D2ECE7',
          200: '#A5D9D0',
          300: '#6DBFB3',
          400: '#3CA391',
          500: '#1E7F6F',
          600: '#0F766E',
          700: '#0B5D56',
          800: '#11453F',
          900: '#0E3531',
          950: '#072220',
        },
        ink: {
          primary: '#1E201D',   // espresso off-black, never pure black
          secondary: '#6E6A61',
          tertiary: '#A39F94',
        },
        // Portrait accent - warm cream for hero
        cream: {
          DEFAULT: '#F4EFE4',
          light: '#FAF6EE',
          deep: '#E6DECC',
        },
        semantic: {
          success: '#2FA06A',
          warning: '#D99A2B',
          error: '#C4453B',
        },
        category: {
          word: '#2563eb',
          excel: '#16a34a',
          powerpoint: '#dc2626',
        }
      },
      fontFamily: {
        sans: ['"Switzer"', '"SF Pro Display"', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        display: ['"Cabinet Grotesk"', '"SF Pro Display"', '"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        serif: ['"Newsreader"', '"Playfair Display"', 'Georgia', 'serif'],
      },
      borderRadius: {
        'card': '16px',
        'panel': '24px',
        'button': '9999px',
        'pill': '9999px',
      },
      boxShadow: {
        'whisper': '0 20px 40px -15px rgba(14,53,49,0.08)',
        'hover': '0 12px 28px -12px rgba(14,53,49,0.18)',
        'soft': '0 2px 12px rgba(14,53,49,0.06)',
        'glow': '0 10px 40px -10px rgba(15,118,110,0.45)',
        'inner-light': 'inset 0 1px 0 rgba(255,255,255,0.12)',
      },
      animation: {
        'fade-in': 'fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up': 'slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up-slow': 'slideUp 0.7s cubic-bezier(0.16, 1, 0.3, 1)',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
        'shimmer': 'shimmer 1.8s linear infinite',
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
          '50%': { opacity: '0.65' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-300px 0' },
          '100%': { backgroundPosition: '300px 0' },
        },
      },
      backgroundImage: {
        'grain': "radial-gradient(circle at 20% 20%, rgba(21,94,85,0.06), transparent 40%), radial-gradient(circle at 80% 0%, rgba(15,118,110,0.08), transparent 45%)",
      },
      letterSpacing: {
        'widest-2': '0.25em',
      }
    },
  },
  plugins: [],
}
