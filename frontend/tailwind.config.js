/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // --- Existing app tokens (kept so current pages keep working) ---
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
        error: "#DC2626",

        // --- SparkLab design-system tokens (Phase 1) ---
        page: "#F1F5E0",        // pale lime-cream page background
        ink: "#0A0A0A",         // primary text / black
        muted: "#55554A",       // muted body text
        orange: "#FF4F00",      // accent
        // AA-safe orange: white text on `orange` is only ~3.3:1, so surfaces
        // that carry white body text use this (~5.4:1). Pure `orange` stays for
        // accents, icons and dark-on-orange fills.
        "orange-deep": "#C13A00",
        green: "#0F7B3F",       // secondary accent
        lavender: "#DDB9FB",    // tertiary accent
        cardwhite: "#FFFFFF"    // white cards
      },
      borderRadius: {
        pill: "9999px",  // nav pills, tags, buttons
        card: "32px",    // cards
        inner: "20px"    // inner images
      },
      maxWidth: {
        container: "1600px"
      },
      fontFamily: {
        // Site-wide font updates for better readability and modern look
        sans: ['"Outfit"', '"Inter"', "sans-serif"],
        mono: ['"IBM Plex Mono"', '"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        display: ['"Outfit"', '"Inter"', "sans-serif"]
      },
      letterSpacing: {
        heading: "-0.02em"
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
        'section-y': '120px',   // desktop section vertical padding
        'container-x': '40px'   // desktop horizontal padding
      }
    },
  },
  plugins: [],
};
