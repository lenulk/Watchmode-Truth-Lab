export default {
  server: {
    host: '127.0.0.1',
    strictPort: true,
    watch: process.env.WTL_DISABLE_WATCH === '1'
      ? null
      : { usePolling: process.env.WTL_USE_POLLING === '1' },
  },
}
