export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        fadeIn: "fadeIn 0.6s ease 0.2s backwards",
        rotatePattern: "rotatePattern 20s linear infinite",
        shimmer: "shimmer 2s ease-in-out infinite",
      },
    },
  },
  plugins: [
    function ({ addUtilities }) {
      const newUtilities = {
        ".scrollbar-thin": {
          scrollbarWidth: "thin",
        },
        ".scrollbar-webkit": {
          "&::-webkit-scrollbar": {
            width: "8px",
            height: "6px",
          },
          "&::-webkit-scrollbar-track": {
            backgroundColor: "rgb(243 244 246)",
            borderRadius: "3px",
          },
          "&::-webkit-scrollbar-thumb": {
            backgroundColor: "rgb(209 213 219)",
            borderRadius: "3px",
            "&:hover": {
              backgroundColor: "rgb(156 163 175)",
            },
          },
        },
        ".dark .scrollbar-webkit": {
          "&::-webkit-scrollbar-track": {
            backgroundColor: "rgb(31 41 55)",
          },
          "&::-webkit-scrollbar-thumb": {
            backgroundColor: "rgb(75 85 99)",
            "&:hover": {
              backgroundColor: "rgb(107 114 128)",
            },
          },
        },
      };
      addUtilities(newUtilities);
    },
  ],
};
