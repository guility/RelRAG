/** RelRAG frontend configuration. Override via window.RELRAG_CONFIG before scripts load. */
window.RELRAG_CONFIG = window.RELRAG_CONFIG || {
  API_URL: "http://localhost:8000",
  KEYCLOAK_URL: "http://localhost:8080",
  KEYCLOAK_REALM: "relrag",
  KEYCLOAK_CLIENT_ID: "relrag-app",
};
