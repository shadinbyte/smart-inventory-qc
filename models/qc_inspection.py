from odoo import models, fields, api


class QCInspection(models.Model):
    _name = 'qc.inspection'
    _description = 'Quality Control Inspection'

    name = fields.Char(string='Reference', default='New', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number')
    inspector_id = fields.Many2one('res.users', string='Inspector',
                                   default=lambda self: self.env.user)
    inspection_date = fields.Datetime(string='Inspection Date',
                                      default=fields.Datetime.now)
    picking_id = fields.Many2one('stock.picking', string='Source Transfer')
    notes = fields.Text(string='Inspection Notes')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('pass', 'Passed'),
        ('fail', 'Failed'),
    ], default='draft')

    pass_rate = fields.Float(string='Pass Rate %', compute='_compute_pass_rate', store=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('qc.inspection') or 'New'
        return super().create(vals)

    @api.depends('state')
    def _compute_pass_rate(self):
        for record in self:
            if record.state == 'pass':
                record.pass_rate = 100.0
            elif record.state == 'fail':
                record.pass_rate = 0.0
            else:
                record.pass_rate = 0.0

    # FIXED: Match the button names in XML
    def action_start_inspection(self):
        self.state = 'in_progress'

    def action_pass(self):
        self.state = 'pass'

    def action_fail(self):
        self.state = 'fail'


    @api.model
    def cron_auto_create_incoming_qc(self):
        """Automatically create QC for incoming transfers"""
        incoming_done = self.env['stock.picking'].search([
            ('picking_type_code', '=', 'incoming'),
            ('state', '=', 'done'),
            ('qc_inspection_count', '=', 0)  # No existing QC
        ], limit=10)  # Limit to avoid too many at once

        for picking in incoming_done:
            if picking.move_ids_without_package:
                self.create({
                    'product_id': picking.move_ids_without_package[0].product_id.id,
                    'picking_id': picking.id,
                })