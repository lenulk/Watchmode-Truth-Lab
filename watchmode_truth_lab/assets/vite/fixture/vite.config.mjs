export default {
  server: {
    watch: process.env.WTL_DISABLE_WATCH === '1' ? null : {
      usePolling: process.env.WTL_USE_POLLING === '1',
      // Avoid transforming the truncate/write interval of an ordinary save.
      awaitWriteFinish: { stabilityThreshold: 200, pollInterval: 20 },
      ignored: ['**/.wtl-browser*'],
    },
  },
};
