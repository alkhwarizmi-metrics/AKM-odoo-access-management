{
    "name": "OAuth2.0 API Access Management",
    "version": "18.0.1.0.0",
    "summary": "OAuth2.0 API for accessing Odoo data",
    "description": """
        OAuth2.0 API Access Management for Odoo

        Key Features:
        ------------
        * Standard OAuth2.0 authentication flow
        * Model and field-level access control
        * Token lifecycle management
        * Request logging and monitoring
        * Granular permissions system
        * CSRF protection

        Security:
        --------
        * CSRF protection
        * Token encryption
        * Field-level access control
        * Model-level permissions
        * Request validation
    """,
    "author": "Alkhwarizmi Metrics",
    "website": "https://github.com/alkhwarizmi-metrics/AKM-odoo-access-management",
    "category": "Technical/API",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/akm_oauth_client.xml",
        "views/akm_oauth_consent_template.xml",
        "views/akm_request_log.xml",
    ],
    "images": [
        "static/description/banner.png",
        "static/description/icon.png",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "maintainer": "Alkhwarizmi Metrics",
    "support": "https://github.com/alkhwarizmi-metrics/AKM-odoo-access-management/issues",
}
