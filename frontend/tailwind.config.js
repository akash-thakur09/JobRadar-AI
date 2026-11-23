/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // JobRadar AI Approved Identity: Modern Editorial + Career Intelligence Terminal
        terminal: {
          dark: "#161616",          // Primary dark
          secondary: "#20201F",     // Secondary dark
          elevated: "#292927",      // Elevated dark / dark surface border
          warm: "#F3EFE7",          // Warm canvas background
          warmSurface: "#FAF8F5",   // Card surface
          warmBorder: "#DCD7CD",    // Warm border
          muted: "#AAA69E",         // Muted text
          primary: "#FF5A36",       // Primary action orange
          primaryHover: "#E04826",  // Action orange active / hover
          lime: "#D6FF3F",          // Opportunity lime
          limeText: "#3B4D00",      // High contrast text on lime
          ai: "#8DB4FF",            // AI intelligence blue
          aiText: "#183B7E",        // High contrast text on AI blue
          success: "#5BCB8A",       // Success green
          successText: "#185C36",   // High contrast text on success green
          amber: "#E6B84D",         // Pending amber
          amberText: "#6E4C00",     // High contrast text on amber
          error: "#E05A47",         // Error red
          errorText: "#8A1F11",     // High contrast text on error red
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        display: ["Space Grotesk", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        subtle: "0 1px 2px rgba(22, 22, 22, 0.04)",
        card: "0 1px 3px rgba(22, 22, 22, 0.05), 0 1px 2px rgba(22, 22, 22, 0.03)",
        dropdown: "0 10px 25px -3px rgba(22, 22, 22, 0.15), 0 4px 6px -2px rgba(22, 22, 22, 0.05)",
      },
      borderRadius: {
        sharp: "2px",
        card: "8px",
      },
    },
  },
  plugins: [],
};
