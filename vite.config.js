import { defineConfig } from 'vite';

// Chetan's deployed API. Requests are proxied server-side, so the browser only
// ever talks to the frontend's own origin: the API needs no CORS entry for
// localhost (it does not have one) or for whatever host a forwarded Codespace
// port happens to use. Point this back at http://127.0.0.1:8000 to develop
// against a local backend.
const apiTarget = process.env.VITE_API_PROXY_TARGET
  ?? 'https://silver-spring-community-census.onrender.com';

// changeOrigin rewrites the Host header, which Render needs to route the
// request to the right service.
const proxy = { '/api': { target: apiTarget, changeOrigin: true } };

export default defineConfig({
  server: { port: 5173, strictPort: true, proxy },
  preview: { proxy },
});
