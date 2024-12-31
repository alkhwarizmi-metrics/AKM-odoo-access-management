# OAuth

A custom OAuth2-like implementation for Odoo that allows secure API access management.

## Features

- OAuth2-like authentication flow
- API access management
- Model-level permissions
- Token lifecycle management
- Secure credential handling
- Standard Request & response schema

## Required Models

### AkmOAuthClient

Manages OAuth clients and their permissions.

```python
class AkmOAuthClient(models.Model):
    name = fields.Char()           # Application name
    client_id = fields.Char()      # Public identifier
    client_secret = fields.Char()  # Secret key
    redirect_uri = fields.Char()   # Callback URL
    scope = fields.Selection()     # read/write/admin access level
```
### AkmClientPermission
Manages field-level permissions for each client-model combination.

```python
class AkmClientPermission(models.Model):
    client_id = fields.Many2one()  # Reference to AkmOAuthClient
    model_id = fields.Many2one()   # Reference to ir.model
```

### AkmOAuthAuthCode

Handles authorization codes for the OAuth flow.

```python
class AkmOAuthAuthCode(models.Model):
    code = fields.Char()           # One-time authorization code
    expires_at = fields.Datetime() # 5-minute expiration
    used = fields.Boolean()        # Prevents replay attacks
```

### AkmOAuthToken

Manages access tokens for API authentication.

```python
class AkmOAuthToken(models.Model):
    access_token = fields.Char()   # API access credential
    refresh_token = fields.Char()  # Token renewal credential
    expires_at = fields.Datetime() # Token expiration
```


## Authentication Flow

1. Client Registration

```bash

POST {{HOST}}/{{MODULE}}/v1/register
{
    "name": "My App",
    "redirect_uri": "https://myapp.com/callback"
}

```


2. Authorization Request

```bash

GET {{HOST}}/{{MODULE}}/v1/authorize
?client_id=abc123
&response_type=code

```

3. Authorization Response

```bash

HTTP/1.1 302 Found
Location: https://myapp.com/callback?code=temp_auth_code

```


4. Token Request

```bash

POST {{HOST}}/{{MODULE}}/v1/token
{
    "grant_type": "authorization_code",
    "code": "temp_auth_code",
    "client_id": "abc123",
    "client_secret": "xyz789"
}

```
5. Token Response
```json

{
    "jsonrpc": "2.0",
    "id": null,
    "result": {
        "status": "success",
        "status_code": 200,
        "message": "Operation successful",
        "data": {
            "access_token": "eyJ0eX...",
            "refresh_token": "eyJhbG...",
            "token_type": "Bearer",
            "expires_in": 3600
        }
    }
}

```


## Authentication Flow

- One-time authorization codes
- Token expiration
- Scope-based access control
- Model-level permissions
- Credential hashing


# Setup

1. Clone the repository:
```
git clone git@github.com:alkhwarizmi-metrics/AKM-odoo-access-management.git
```

2. Add to Odoo addons path:

```
cp -r AKM-odoo-access-management /path/to/odoo/addons/
```

3. Install the module:

```
./odoo-bin -i AKM-odoo-access-management
```

# Get Permissions & Reading the Records

Below are new endpoints to inspect accessible models and read data.
Check which models a client can access.

## Get Permissions

### Endpoint

```bash
GET {{HOST}}/{{MODULE}}/v1/permissions
```

Example Request
```bash
curl -X GET "https://example.com/alkhwarizmi_metrics_api/v1/permissions" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Example Response
```json
{
  "jsonrpc": "2.0",
  "id": null,
  "result": {
    "status": "success",
    "status_code": 200,
    "message": "Operation successful",
    "data": {
      [
        {
          "model_name": "res.partner",
          "model_description": "Contact",
          "fields": [
            {
              "name": "name",
              "type": "char",
              "required": false,
              "readonly": false,
              "string": "Name"
            },
            ...
        }
        ...
      ]
    }
  }
}
```
## Reading the Records

Record is similar to what we know a row in database. So by utilizing this endpoint we can read only accessible models that Odoo user allows to be accessible by Client in model `AkmOAuthClient`

Retrieve records from a specified model using various filters and pagination.
```bash
GET {{HOST}}/{{MODULE}}/v1/records
```

## Query Parameters
- `model_name` (required): Name of the model (e.g., "res.partner")
- `fields`: Comma-separated list of fields to return, or `"*"` for all
- `page`, `per_page`: Pagination controls
- `date_gte`, `date_lte`, `targetted_date_field`: Filter by dates
- `date_time_gte`, `date_time_lte`, `targetted_datetime_field`: Filter by datetimes

Example Request:

```bash
curl -X GET "https://example.com/alkhwarizmi_metrics_api/v1/data/read?model_name=res.partner&page=1&per_page=5" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Example Response 
```json

{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "status": "success",
    "status_code": 200,
    "message": "Operation successful",
    "data": {
      "records": [
        {
          "id": 42,
          "name": ".."
        },
        ...
      ],
      "pagination": {
        "page": 1,
        "per_page": 5,
        "total_records": 23,
        "total_pages": 5
      }
    }
  }
}

```

## Filter by date range 
Format: YYYY-MM-DD HH:mm:ss
Timezone: UTC (Odoo's default)
Common fields: create_date, write_date, but user can provide any accessible datetime field

```bash
# Basic datetime range query
curl -X GET "https://example.com/alkhwarizmi_metrics_api/v1/records" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "res.partner",
    "date_time_gte": "2024-01-01 00:00:00",
    "date_time_lte": "2024-01-31 23:59:59",
    "targetted_datetime_field": "create_date"
  }'

# Query for last month's records
curl -X GET "https://example.com/alkhwarizmi_metrics_api/v1/records" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "res.partner",
    "date_time_gte": "2023-12-01 00:00:00",
    "date_time_lte": "2023-12-31 23:59:59",
    "targetted_datetime_field": "write_date"
  }'
```

## License
<!-- Point to LICENSE -->