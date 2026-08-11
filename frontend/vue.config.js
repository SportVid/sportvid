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
    client: {
      overlay: {
        runtimeErrors: (error) =>
          error.message !== "ResizeObserver loop completed with undelivered notifications.",
      },
    },
  },
};
