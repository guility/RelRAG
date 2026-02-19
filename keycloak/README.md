# Keycloak — тестовая конфигурация

## Предзагруженный realm

При `docker compose up` Keycloak автоматически импортирует realm `relrag` из `import/relrag-realm.json`.

## Тестовые учётные данные

| Роль | Пользователь | Пароль |
|------|--------------|--------|
| Admin | admin | admin |
| Тестовый пользователь | testuser | testpass |

## Клиент relrag-api

- **Client ID:** relrag-api
- **Client Secret:** relrag-api-secret
- **Тип:** Confidential (для introspect JWT)

## Получение токена (для тестов)

```bash
# Получить токен для testuser
curl -X POST "http://localhost:8080/realms/relrag/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=relrag-api" \
  -d "client_secret=relrag-api-secret" \
  -d "username=testuser" \
  -d "password=testpass"
```

Использование токена в заголовке: `Authorization: Bearer <access_token>`
