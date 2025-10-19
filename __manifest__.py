{
    'name': 'Smart Inventory & Quality Control',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Automated quality control system for Odoo 18',
    'description': """
        Smart QC System with automated inspections, stock integration, and reporting
    """,
    'author': 'Your Name',
    'website': '',
    'depends': ['base', 'stock', 'product', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/automation_cron.xml',
        'views/menus.xml',
        'views/qc_inspection_views.xml',
        'views/stock_views.xml',
        'views/dashboard_views.xml',
        'report/qc_report_templates.xml',
        'report/qc_report_actions.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}