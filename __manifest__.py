{
    "name": "Alkhwarizmi Metrics API",
    "version": "1.0",
    "summary": "OAuth2.0 API for accessing Odoo data",
    "description": "This addon provides OAuth2.0 endpoints and allows access to Odoo models via REST API.",
    "author": "Alkhwarizmi Metrics",
    "category": "Technical",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/akm_oauth_client.xml",
        "views/akm_oauth_consent_template.xml",
        "views/akm_request_log.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
