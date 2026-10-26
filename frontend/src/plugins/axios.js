import axios from 'axios';

// No baseURL: every store prefixes its paths with config.API_LOCATION ("/api").
export default axios.create({
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  // axios >= 1.6 only sends the CSRF token to the page's own origin by default. The API is
  // same-origin everywhere today; this keeps the token flowing if API_LOCATION ever
  // points at another origin. Every request made with this instance goes to our backend.
  withXSRFToken: true,
});
