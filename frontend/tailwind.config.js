/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: "#0f766e",
        accent: {
          DEFAULT: "#1D4ED8",
          hover: "#1E3A8A",
          light: "#DBEAFE"
        },
        surface: "#FFFFFF",
        background: "#F3F4F6",
        textPrimary: "#111827",
        textSecondary: "#4B5563",
        error: "#DC2626"
      },
      fontSize: {
        'base': ['1.125rem', '1.75rem'],
        'lg': ['1.25rem', '1.75rem'],
        'xl': ['1.5rem', '2rem'],
        '2xl': ['1.875rem', '2.25rem'],
      },
      spacing: {
        'touch': '44px',
        'touch-lg': '56px',
      }
    },
  },
  plugins: [],
};
