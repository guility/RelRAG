/** API client with Bearer token and error handling. */
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

  /** User-friendly message from API error or network error. */
  function getErrorMessage(err) {
    if (!err) return "Неизвестная ошибка";
    if (err.message === "Failed to fetch" || err.message === "NetworkError when fetching") {
      return "Нет связи с сервером. Проверьте подключение и настройки API.";
    }
    var msg = err.message || err.error || "";
    var status = err.status || err.statusCode;
    if (status === 401) return "Требуется авторизация. Выполните вход.";
    if (status === 403) return "Доступ запрещён.";
    if (status === 404) return "Ресурс не найден.";
    if (status === 400) return msg || "Неверный запрос.";
    if (status >= 500) return msg || "Ошибка сервера. Попробуйте позже.";
    if (msg && msg.length < 200) return msg;
    return msg || "Произошла ошибка. Попробуйте ещё раз.";
  }

  /** Show error in element by id; optional prefix. */
  function showError(err, targetId, prefix) {
    var text = getErrorMessage(err);
    var el = targetId ? document.getElementById(targetId) : null;
    if (el) {
      el.innerHTML = "<p class=\"error\">" + (prefix ? prefix + " " : "") + escapeHtml(text) + "</p>";
      el.style.display = "";
    } else {
      console.error("RelRAG API error:", err);
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  window.relragApi = {
    get: function (path) {
      return fetch(API_URL + path, {
        method: "GET",
        headers: getHeaders(),
        credentials: "omit",
      });
    },

    post: function (path, body) {
      return fetch(API_URL + path, {
        method: "POST",
        headers: getHeaders(),
        body: body ? JSON.stringify(body) : undefined,
        credentials: "omit",
      });
    },

    delete: function (path) {
      return fetch(API_URL + path, {
        method: "DELETE",
        headers: getHeaders(),
        credentials: "omit",
      });
    },

    handleResponse: function (res) {
      if (res.status === 401) {
        if (window.relragAuth && window.relragAuth.login && !window.relragAuth._loginRedirecting) {
          window.relragAuth._loginRedirecting = true;
          window.relragAuth.login();
        }
        return Promise.reject({ status: 401, message: "Unauthorized" });
      }
      if (res.status === 204) return Promise.resolve(null);
      return res.json().then(function (data) {
        if (!res.ok) {
          return Promise.reject({
            status: res.status,
            message: (data && (data.error || data.message)) || res.statusText || "Request failed",
          });
        }
        return data;
      }).catch(function (e) {
        if (e && (e.status !== undefined || e.message)) return Promise.reject(e);
        if (res.ok) return Promise.resolve(null);
        return Promise.reject({ status: res.status, message: res.statusText || "Request failed" });
      });
    },

    getErrorMessage: getErrorMessage,
    showError: showError,
  };
})();
