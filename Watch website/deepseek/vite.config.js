import { defineConfig } from 'vite';

export default defineConfig({
  root: 'site',
  publicDir: '../public',
  base: './',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    assetsInlineLimit: 0,
  },
  server: {
    host: '127.0.0.1',
  },
});
