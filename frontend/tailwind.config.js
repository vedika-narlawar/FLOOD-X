export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {
    colors: { ink: "#0a0f16", panel: "#0f1722", raise: "#141f2d", line: "#1e2b3b", mute: "#7d8da1", sub: "#a9b6c6", text: "#e4ebf3",
              cy: "#22d3ee", bl: "#5b8def", am: "#f5a524", rd: "#ef5350", gr: "#3ecf8e" },
    fontFamily: { sans: ["Inter", "Segoe UI", "system-ui", "-apple-system", "Helvetica Neue", "Arial", "sans-serif"],
                  mono: ["JetBrains Mono", "SFMono-Regular", "Menlo", "Consolas", "monospace"] } } },
  plugins: [],
};
