import axios from 'axios';

export default axios.create({
  baseURL: '/api',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  // axios >= 1.6 only sends the token to the page's own origin by default. Locally the
  // dev server (:8080) calls the API on :8010, so send it explicitly; every request made
  // with this instance goes to our own backend.
  withXSRFToken: true,
});
