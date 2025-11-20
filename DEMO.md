# IServ Module Interface Demo

This document showcases live examples of the IServ Module interface, illustrating its capabilities and how to interact with it.

## Example 1: Authentication

### Request
```http
POST /api/authenticate
Content-Type: application/json

{
  "username": "<your_username>",
  "password": "<your_password>"
}
```

### Response
```json
{
  "token": "<your_jwt_token>",
  "expires_in": 3600
}
```

## Example 2: Fetching User Data

### Request
```http
GET /api/user
Authorization: Bearer <your_jwt_token>
```

### Response
```json
{
  "id": "123",
  "username": "<your_username>",
  "roles": ["admin", "user"],
  "email": "user@example.com"
}
```

## Example 3: Creating a New Entry

### Request
```http
POST /api/entries
Authorization: Bearer <your_jwt_token>
Content-Type: application/json

{
  "title": "New Entry",
  "content": "This is a new entry content."
}
```

### Response
```json
{
  "id": "456",
  "title": "New Entry",
  "content": "This is a new entry content.",
  "created_at": "2025-11-20T20:37:31Z"
}
```

---

## Conclusion

This DEMO.md file presents fundamental interactions with the IServ Module interface. For further information, consult the module's documentation.