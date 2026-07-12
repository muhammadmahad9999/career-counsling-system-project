/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                dark: "#0E1117",
                "dark-secondary": "#1AA1F5", // Not used directly but referenced in gradients?
                "primary-cyan": "#00E5FF",
                "accent-teal": "#00F5D4",
                "text-gray": "#A8B2D1",
                "card-bg": "rgba(8, 10, 15, 0.9)",
                "card-border": "rgba(255, 255, 255, 0.1)",
            },
            fontFamily: {
                grotesk: ['"Space Grotesk"', 'sans-serif'],
            },
            backgroundImage: {
                'hero-gradient': 'radial-gradient(circle at 76% 22%, rgba(0, 229, 255, 0.2) 0%, rgba(0, 119, 255, 0.1) 40%, rgba(14, 17, 23, 1) 100%)', // Adjusted opacity for background
                'card-gradient': 'radial-gradient(circle at 50% 50%, rgba(0, 229, 255, 0.05) 0%, rgba(14, 17, 23, 0) 100%)',
            }
        },
    },
    plugins: [],
}
