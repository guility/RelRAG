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
            resolve(authenticated);
          })
          .catch(reject);
      });
    },

    login: function () {
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
        ? keycloak.updateToken(30).catch(function () {
            keycloak.login();
          })
        : Promise.reject(new Error("Not initialized"));
    },
  };
})();
