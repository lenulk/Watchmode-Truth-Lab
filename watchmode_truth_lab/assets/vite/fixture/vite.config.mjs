export default {
  server: {
    watch: process.env.WTL_DISABLE_WATCH === '1' ? null : {
      usePolling: process.env.WTL_USE_POLLING === '1',
      ignored: ['**/.wtl-browser*'],
    },
  },
};
