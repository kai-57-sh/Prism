import colors from 'tailwindcss/colors';

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
    },
    extend: {
      colors: {
        primary: colors.teal,
        background: '#F9FAFB',
      }
    },
  },
  plugins: [],
};
