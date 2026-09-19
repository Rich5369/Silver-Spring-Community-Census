import { defineConfig } from 'vite';

// Browser requests stay on the frontend origin, including forwarded Codespace ports.
const proxy = { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } };

export default defineConfig({
  server: { port: 5173, strictPort: true, proxy },
  preview: { proxy },
});
