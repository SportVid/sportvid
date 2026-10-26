// Same-origin paths on every environment: nginx proxies them on the servers and on
// port 80 of the local frontend container; `npm run serve` proxies them in vue.config.js.
module.exports = {
  API_LOCATION: "/api",
  THUMBNAIL_LOCATION: "/thumbnails",
};
