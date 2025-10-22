{
    "name": "Smart Inventory & Quality Control",
    "version": "18.0.1.0.0",
    "category": "Inventory/Quality",
    "summary": "Automated quality control inspections for incoming transfers",
    "description": """
        Smart QC System Features:
        - Automated quality inspections for incoming transfers
        - Multi-criteria checklist support
        - Quantity-based pass/fail tracking
        - Supplier quality analytics
        - Professional PDF reports
        - Email notifications
        - Real-time dashboard
    """,
    "author": "Shadin",
    "website": "https://github.com/shadinbyte",
    "depends": [
        "base",
        "stock",
        "product",
        "mail",
        "web",
    ],
    "data": [
        "security/qc_security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "data/automation_cron.xml",
        "data/mail_template.xml",
        "views/qc_inspection_views.xml",
        "views/qc_dashboard_template.xml",
        "views/stock_views.xml",
        "views/dashboard_views.xml",
        "report/qc_report_templates.xml",
        "report/qc_report_actions.xml",
        "views/menus.xml",
    ],
    "demo": [],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
