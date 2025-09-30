import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
  plugins: [vue()],
  root:'.',
  build: {
    outDir: resolve(__dirname, '..', 'static', 'django_app_rag', 'dist'),
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: {
        main_vue: resolve(__dirname, 'frontend', 'main.js'),
      },
    },
  },
  server: {
    port: 3000
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'frontend')
    },
    modules: [
      resolve(__dirname, '../../bundles/node_modules'),
      'node_modules'
    ]
  }
}); 