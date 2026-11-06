import axios from 'axios';

// No baseURL: every store prefixes its paths with config.API_LOCATION ("/api").
const api = axios.create({
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  // axios >= 1.6 only sends the CSRF token to the page's own origin by default. The API is
  // same-origin everywhere today; this keeps the token flowing if API_LOCATION ever
  // points at another origin. Every request made with this instance goes to our backend.
  withXSRFToken: true,
});

// The API answers errors with real HTTP status codes (ADR 0005). Errors that used to come
// with HTTP 200 carry the X-Legacy-Error-Status header (backend/utils/api.py); hand those to
// the stores as before, since most stores read res.data.status instead of catching. Errors
// that were already 4xx/5xx still reject. Remove this once every store handles status codes.
api.interceptors.response.use(undefined, (error) => {
  if (error.response?.headers?.['x-legacy-error-status']) {
    return error.response;
  }
  return Promise.reject(error);
});

export default api;
