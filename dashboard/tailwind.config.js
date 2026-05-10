/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}"] ,
  theme: {
    extend: {
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"]
      },
      colors: {
        ink: "#0b0e10",
        coal: "#121517",
        fog: "#e6ecef",
        ember: "#ff6a3d",
        sky: "#7dd3fc",
        moss: "#b7f3b2"
      },
      boxShadow: {
        glow: "0 0 40px rgba(125, 211, 252, 0.25)"
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" }
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-8px)" }
        }
      },
      animation: {
        rise: "rise 700ms ease-out both",
        float: "float 5s ease-in-out infinite"
      }
    }
  },
  plugins: []
};
