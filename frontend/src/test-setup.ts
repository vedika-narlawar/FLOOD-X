import "@testing-library/jest-dom/vitest";

// jsdom lacks ResizeObserver, which recharts' ResponsiveContainer requires.
class RO { observe() {} unobserve() {} disconnect() {} }
(globalThis as any).ResizeObserver = (globalThis as any).ResizeObserver ?? RO;
