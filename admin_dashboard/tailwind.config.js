/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: "#050608",
          card: "#0d0f13",
          border: "#1d242e",
          glow: "#00f0ff",
          text: "#e2e8f0",
          success: "#00ff66",
          danger: "#ff0033",
          fbi: "#101622"
        }
      },
      fontFamily: {
        poppins: ["Poppins", "sans-serif"],
        playfair: ["Playfair Display", "serif"],
        sfpro: ["SF Pro Display", "-apple-system", "BlinkMacSystemFont", "Inter", "sans-serif"]
      },
      boxShadow: {
        'glow-yellow': '0 0 15px rgba(234, 179, 8, 0.15)',
        'glow-green': '0 0 15px rgba(0, 255, 102, 0.15)',
        'glow-red': '0 0 15px rgba(255, 0, 51, 0.15)',
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)'
      }
    },
  },
  plugins: [],
}
