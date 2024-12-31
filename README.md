# Odoo OAuth2.0 

A custom OAuth2-like implementation for Odoo that allows secure API access management.


## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Access Control](#access-control)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Features
- OAuth2.0 authentication flow
- ModelField-level access control
- Token lifecycle management
- Model-specific permissions
- Detailed API documentation
- Easy integration

## Requirements
- Odoo 16 or later
- (Rest configure python and postgres according to Odoo requirements, and no sepcific installations required for this addon)

## Installation

```bash
# Clone the repository
git clone git@github.com:alkhwarizmi-metrics/AKM-odoo-access-management.git

# Add to Odoo addons path
cp -r AKM-odoo-access-management /path/to/odoo/addons/

# Install required Python packages
pip install -r requirements.txt

# Install the module
./odoo-bin -i alkhwarizmi_metrics_api
```


## API reference

1. Client Registration

```bash

POST {{HOST}}/{{MODULE}}/v1/register

{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "name": "client name",
        "redirect_uri": "https://myapp.com/callback"
    },
    "id": null
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
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "grant_type": "authorization_code",
      "code": "temp_auth_code",
      "client_id": "abc123",
      "client_secret": "xyz789"
    }
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

# Access Control
By default we are not creating any Permissions for AuthClients, even clients are successfully registered and verified we have to set permissions for this particular client. 

1. Go to settings
2. Open "AKM Oauth2.0 Clients"
3. Open the record that we want to update 
4. Click "Add a line" in Permissions tab to further add models and fields

Note: At any point if Odoo users want to revoke access of Auth Clients, they can just simple set `is_active` to `False` .


# Get Permissions & Reading the Records

Below are new endpoints to get permissions regarding models and read data. Check which models a client can access.

## Get Permissions

```bash
GET {{HOST}}/{{MODULE}}/v1/permissions
```

#### Example Request
```bash
curl -X GET "https://example.com/alkhwarizmi_metrics_api/v1/permissions" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Example Response
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

### Params
- `model_name` (required): Name of the model (e.g., "res.partner")
- `fields`: Comma-separated list of fields to return, or `"*"` for all
- `page`, `per_page`: Pagination controls
- `date_gte`, `date_lte`, `targetted_date_field`: Filter by dates
- `date_time_gte`, `date_time_lte`, `targetted_datetime_field`: Filter by datetimes


```bash
GET {{HOST}}/api/v1/records
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json
{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "model_name": "res.partner",
        "fields": "name,email,phone",
        "page": 1,
        "per_page": 10,
        "date_time_gte": "2024-01-01 00:00:00",
        "date_time_lte": "2024-01-31 23:59:59",
        "targetted_datetime_field": "create_date"
    },
    "id": null
}
```


#### Example Request:

```bash
curl -X GET "https://example.com/alkhwarizmi_metrics_api/v1/data/read?model_name=res.partner&page=1&per_page=5" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Example Response 
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

### Filter by date range 
Format: YYYY-MM-DD HH:mm:ss
Timezone: UTC (Odoo's default)
Common fields: create_date, write_date, but user can provide any accessible datetime field

## Troubleshooting

Common Issues:
   - If API Json requests doesn't requires to pass any body parameters though you have to provide empty dict to follow jsonrpc 2.0

## License
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

This project is licensed under the GNU Lesser General Public License v3.0 - see the [LICENSE](LICENSE) file for details.