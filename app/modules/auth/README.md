# Auth API

Этот документ описывает только auth-эндпоинты проекта Nobal eduadviser и предназначен для мобильной разработки.

## Базовая информация

- Base URL: `/api/v1/auth`
- Формат тела запросов: `application/json`
- Формат успешных ответов: `{ "success": true, "data": ... }`
- Формат ошибок API: `{ "success": false, "error": { "code": "...", "message": "...", "details": ... } }`
- Все refresh-токены хранятся на сервере и ротируются при обновлении пары токенов.

## Авторизация

Для защищенных эндпоинтов передавайте access token в заголовке:

```http
Authorization: Bearer <access_token>
```

В этом модуле авторизация нужна для:

- `POST /logout`
- `POST /change-password`

## Общие правила пароля

Пароль должен:

- содержать минимум 8 символов;
- содержать хотя бы одну заглавную букву;
- содержать хотя бы одну строчную букву;
- содержать хотя бы одну цифру.

Это относится к:

- `POST /register`
- `POST /reset-password`
- `POST /change-password`

## Эндпоинты

### 1. Регистрация

`POST /api/v1/auth/register`

Создает нового пользователя и сразу возвращает пару токенов.

#### Request body

```json
{
  "email": "student@example.com",
  "full_name": "Student Name",
  "password": "StrongPass123",
  "group_type": "D",
  "course_year": 2,
  "gpa": 3.5,
  "ielts_passed": false,
  "ielts_score": null,
  "sat_passed": false,
  "sat_score": null
}
```

#### Поля

- `email` — обязательный email.
- `full_name` — от 2 до 255 символов.
- `password` — от 8 до 128 символов, с требованиями к сложности.
- `group_type` — только `"D"` или `"F"`.
- `course_year` — только `2` или `3`.
- `gpa` — необязательное число от `0.0` до `4.0`.
- `ielts_passed` — boolean, по умолчанию `false`.
- `ielts_score` — необязательное число от `0.0` до `9.0`.
- `sat_passed` — boolean, по умолчанию `false`.
- `sat_score` — необязательное число от `400` до `1600`.

#### Response 201

```json
{
  "success": true,
  "data": {
    "access_token": "<access_token>",
    "refresh_token": "<refresh_token>",
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "student@example.com",
      "full_name": "Student Name",
      "role": "student"
    }
  }
}
```

#### Ошибки

- `409 CONFLICT` — пользователь с таким email уже существует.
- `422 UNPROCESSABLE_ENTITY` — ошибка валидации тела запроса.

### 2. Логин

`POST /api/v1/auth/login`

Возвращает access token и refresh token для существующего пользователя.

#### Rate limit

- `5/minute`

#### Request body

```json
{
  "email": "student@example.com",
  "password": "StrongPass123"
}
```

#### Response 200

```json
{
  "success": true,
  "data": {
    "access_token": "<access_token>",
    "refresh_token": "<refresh_token>",
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "student@example.com",
      "full_name": "Student Name",
      "role": "student"
    }
  }
}
```

#### Ошибки

- `401 UNAUTHORIZED` — неверный email или пароль.
- `403 FORBIDDEN` — аккаунт деактивирован.
- `429 TOO_MANY_REQUESTS` — превышен лимит запросов.

### 3. Обновление токенов

`POST /api/v1/auth/refresh`

Меняет refresh token на новую пару токенов. Старый refresh token становится недействительным.

#### Request body

```json
{
  "refresh_token": "<refresh_token>"
}
```

#### Response 200

```json
{
  "success": true,
  "data": {
    "access_token": "<new_access_token>",
    "refresh_token": "<new_refresh_token>"
  }
}
```

#### Ошибки

- `401 UNAUTHORIZED` — refresh token не найден, уже использован, просрочен или пользователь недоступен.

### 4. Выход из системы

`POST /api/v1/auth/logout`

Удаляет refresh token на сервере. Access token продолжит жить до истечения срока действия, поэтому logout в этом backend работает через инвалидирование refresh token.

#### Headers

```http
Authorization: Bearer <access_token>
```

#### Request body

```json
{
  "refresh_token": "<refresh_token>"
}
```

#### Response 200

```json
{
  "success": true,
  "data": null
}
```

### 5. Запрос OTP для сброса пароля

`POST /api/v1/auth/forgot-password`

Отправляет OTP на email пользователя. Если email не существует, ответ все равно будет успешным, чтобы не раскрывать наличие аккаунта.

#### Rate limit

- `3/minute`

#### Request body

```json
{
  "email": "student@example.com"
}
```

#### Response 200

```json
{
  "success": true,
  "data": null
}
```

#### Важно

- OTP хранится в Redis ограниченное время.
- Сам код OTP приходит на email.

### 6. Сброс пароля

`POST /api/v1/auth/reset-password`

Подтверждает OTP и меняет пароль.

#### Request body

```json
{
  "email": "student@example.com",
  "otp": "123456",
  "new_password": "NewStrongPass123"
}
```

#### Response 200

```json
{
  "success": true,
  "data": null
}
```

#### Ошибки

- `400 BAD_REQUEST` с кодом `OTP_EXPIRED` — OTP не найден или истек.
- `400 BAD_REQUEST` с кодом `INVALID_OTP` — неверный OTP.
- `400 BAD_REQUEST` с кодом `VALIDATION_ERROR` — пользователь не найден или тело запроса невалидно.

### 7. Смена пароля

`POST /api/v1/auth/change-password`

Смена пароля для авторизованного пользователя по старому паролю.

#### Headers

```http
Authorization: Bearer <access_token>
```

#### Request body

```json
{
  "old_password": "OldStrongPass123",
  "new_password": "NewStrongPass123"
}
```

#### Response 200

```json
{
  "success": true,
  "data": null
}
```

#### Ошибки

- `400 BAD_REQUEST` с кодом `INVALID_CREDENTIALS` — старый пароль неверный.
- `401 UNAUTHORIZED` — access token отсутствует, просрочен или невалиден.

## Типичные ошибки API

Ниже самые частые коды, с которыми столкнется мобильное приложение:

- `VALIDATION_ERROR` — ошибка бизнес-валидации или некорректные данные.
- `INVALID_CREDENTIALS` — неверный логин, пароль или старый пароль.
- `TOKEN_EXPIRED` — access или refresh token истек.
- `TOKEN_INVALID` — токен невалиден.
- `FORBIDDEN` — доступ запрещен или аккаунт деактивирован.
- `CONFLICT` — конфликт данных, например email уже существует.
- `INVALID_OTP` — неверный OTP.
- `OTP_EXPIRED` — OTP просрочен.

## Практические рекомендации для мобильного клиента

1. После `register` или `login` сразу сохраняйте `access_token` и `refresh_token`.
2. Все защищенные запросы отправляйте с `Authorization: Bearer <access_token>`.
3. Если API вернул `401` из-за истекшего access token, сначала вызывайте `POST /refresh`.
4. После успешного `refresh` обновляйте оба токена, потому что refresh token ротируется.
5. На `forgot-password` не показывайте, существует email или нет, даже если backend ответил успешно.

## Примеры последовательностей

### Логин пользователя

1. `POST /login`
2. Сохранить `access_token`
3. Сохранить `refresh_token`
4. Использовать `Authorization: Bearer ...` для защищенных запросов

### Обновление токена

1. Access token истек
2. `POST /refresh` с текущим refresh token
3. Сохранить новую пару токенов
4. Повторить исходный запрос

### Сброс пароля

1. `POST /forgot-password`
2. Пользователь получает OTP по email
3. `POST /reset-password` с email, OTP и новым паролем
4. При необходимости попросить пользователя заново войти в приложение
