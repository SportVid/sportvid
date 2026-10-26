const webpack = require("webpack");

module.exports = {
  configureWebpack: {
    plugins: [
      new webpack.DefinePlugin({
        __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: JSON.stringify(false),
      }),
    ],
  },
  devServer: {
    // `npm run serve` (port 8080) talks to the API same-origin, like nginx does in
    // production. Targets are the compose service names inside the frontend container.
    proxy: {
      "/api": { target: process.env.SPORTVID_BACKEND_URL || "http://backend:8010" },
      "/thumbnails": { target: process.env.SPORTVID_MEDIA_URL || "http://localhost:80" },
    },
    // gzip would buffer server-sent events (/api/events/stream)
    compress: false,
    client: {
      overlay: {
        runtimeErrors: (error) =>
          error.message !== "ResizeObserver loop completed with undelivered notifications.",
      },
    },
  },
};
