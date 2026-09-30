export default {
  server: {
    host: '127.0.0.1',
    strictPort: true,
    watch: { usePolling: process.env.WTL_USE_POLLING === '1' },
  },
}
