/** API client with Bearer token. */
(function () {
  "use strict";

  const cfg = window.RELRAG_CONFIG || {};
  const API_URL = (cfg.API_URL || "").replace(/\/$/, "");

  function getHeaders() {
    const headers = { "Content-Type": "application/json" };
    const token = window.relragAuth && window.relragAuth.getToken();
    if (token) headers["Authorization"] = "Bearer " + token;
    return headers;
  }

  window.relragApi = {
    get: function (path) {
      return fetch(API_URL + path, { method: "GET", headers: getHeaders() });
    },

    post: function (path, body) {
      return fetch(API_URL + path, {
        method: "POST",
        headers: getHeaders(),
        body: body ? JSON.stringify(body) : undefined,
      });
    },

    delete: function (path) {
      return fetch(API_URL + path, { method: "DELETE", headers: getHeaders() });
    },

    handleResponse: function (res) {
      if (res.status === 401) {
        if (window.relragAuth && window.relragAuth.login) {
          window.relragAuth.login();
        }
        return Promise.reject(new Error("Unauthorized"));
      }
      if (res.status === 204) return Promise.resolve(null);
      return res.json().catch(function () {
        return null;
      });
    },
  };
})();
