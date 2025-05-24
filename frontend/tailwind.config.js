/** @type {import('tailwindcss').Config} */
import defaultTheme from 'tailwindcss/defaultTheme';

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Comfortaa', ...defaultTheme.fontFamily.sans],
      },
      colors: {
        'baby-robin-blue': '#96DED1',
        'baby-robin-blue-dark': '#7ABCB3',
      },
    },
  },
  plugins: [],
}
