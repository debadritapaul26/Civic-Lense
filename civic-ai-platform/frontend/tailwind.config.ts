import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#12243a",
        mist: "#f7f5f0",
        coral: "#c49a42",
        teal: "#117d78",
      },
      boxShadow: {
        soft: "0 16px 45px rgba(23, 32, 51, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
