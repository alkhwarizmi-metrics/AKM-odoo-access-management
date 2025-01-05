# Odoo OAuth2.0 

A custom OAuth2-like implementation for Odoo that allows secure API access management.


## Table of Contents
- [Odoo OAuth2.0](#odoo-oauth20)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [API reference](#api-reference)
- [Access Control](#access-control)
- [Get Permissions \& Reading the Records](#get-permissions--reading-the-records)
  - [Get Permissions](#get-permissions)
      - [Example Request](#example-request)
      - [Example Response](#example-response)
  - [Reading the Records](#reading-the-records)
    - [Params](#params)
      - [Example Response](#example-response-1)
    - [Filter by date range](#filter-by-date-range)
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
- Odoo Version 17.0
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
./odoo-bin -i AKM-odoo-access-management
```


## API reference

1. Register Client

```bash

curl -X POST "{{HOST}}/{{MODULE}}/v1/register" \
     -H "Content-Type: application/json" \
     -d '{
           "jsonrpc": "2.0",
           "method": "call",
           "params": {
               "name": "MyApp",
               "redirect_uri": "https://myapp.com/callback"
           }
         }'

```


2. Authorize

```bash

GET {{HOST}}/{{MODULE}}/v1/authorize
    ?client_id=YOUR_CLIENT_ID
    &response_type=code
    &scope=read
    &state=RANDOM_STATE

```

- Intermediate Step: User sees consent screen and authorizes the requested scope

3. Exchange Token

```bash

curl -X POST "{{HOST}}/{{MODULE}}/v1/token" \
     -H "Content-Type: application/json" \
     -d '{
           "jsonrpc": "2.0",
           "method": "call",
           "params": {
               "grant_type": "authorization_code",
               "code": "AUTH_CODE",
               "client_id": "CLIENT_ID",
               "client_secret": "CLIENT_SECRET"
           }
         }'

```

# Access Control
By default we are not creating any Permissions for AuthClients, even clients are successfully registered and verified we have to set permissions for this particular client. 

1. Go to settings
2. Open "AKM Oauth2.0 Clients"
3. Open the record that we want to update 
4. Click "Add a line" in Permissions tab to further add models and fields

Note: 
1. At any point if Odoo users want to revoke access of Auth Clients, they can just simple set `is_active` to `False` .
2. `id`, `create_date`, `write_date` Fields are being considered as essential fields, you don't have to specifically add them in permissions handling

# Get Permissions & Reading the Records

Below are new endpoints to get permissions regarding models and read data. Check which models a client can access.

## Get Permissions

```bash
GET {{HOST}}/{{MODULE}}/v1/permissions
```

#### Example Request
```bash
curl -X GET "https://example.com/AKM-odoo-access-management/v1/permissions" \
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

# Troubleshooting

Common Issues:
   - If API Json requests doesn't requires to pass any body parameters though you have to provide empty dict to follow jsonrpc 2.0

# License
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

This project is licensed under the GNU Lesser General Public License v3.0 - see the [LICENSE](LICENSE) file for details.