const webpack = require("webpack");

module.exports = {
  // vue may act as a proxy forwarding any requests to the "/api" route
  // devServer: {
  //   proxy:  {
  //     '/api': {
  //       target: 'http://localhost.de:8001'
  //     },
  //   }
  // },
  configureWebpack: {
    plugins: [
      new webpack.DefinePlugin({
        __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: JSON.stringify(false),
      }),
    ],
  },
};
