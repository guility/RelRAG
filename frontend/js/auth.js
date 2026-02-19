/** Keycloak SSO - init, login, token, logout. */
(function () {
  "use strict";

  const cfg = window.RELRAG_CONFIG || {};
  let keycloak = null;

  window.relragAuth = {
    init: function () {
      return new Promise(function (resolve, reject) {
        if (typeof Keycloak === "undefined") {
          reject(new Error("Keycloak not loaded"));
          return;
        }
        keycloak = new Keycloak({
          url: cfg.KEYCLOAK_URL,
          realm: cfg.KEYCLOAK_REALM,
          clientId: cfg.KEYCLOAK_CLIENT_ID,
        });
        keycloak
          .init({ onLoad: "check-sso", checkLoginIframe: false })
          .then(function (authenticated) {
            window.relragAuth._loginRedirecting = false;
            resolve(authenticated);
          })
          .catch(function (err) {
            window.relragAuth._loginRedirecting = false;
            reject(err);
          });
      });
    },

    login: function () {
      window.relragAuth._loginRedirecting = true;
      if (keycloak) keycloak.login();
    },

    logout: function () {
      if (keycloak) keycloak.logout();
    },

    getToken: function () {
      return keycloak ? keycloak.token : null;
    },

    isAuthenticated: function () {
      return keycloak ? keycloak.authenticated : false;
    },

    updateToken: function () {
      return keycloak
        ? keycloak.updateToken(30).catch(function (err) {
            keycloak.login();
            return Promise.reject(err);
          })
        : Promise.reject(new Error("Not initialized"));
    },
  };
})();
