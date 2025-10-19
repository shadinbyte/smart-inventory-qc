from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    qc_inspection_ids = fields.One2many('qc.inspection', 'picking_id', string='QC Inspections')
    qc_inspection_count = fields.Integer(string='QC Count', compute='_compute_qc_count')

    def _compute_qc_count(self):
        for record in self:
            record.qc_inspection_count = len(record.qc_inspection_ids)

    def action_view_qc_inspections(self):
        """Smart button action to view related QC inspections"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'QC Inspections',
            'res_model': 'qc.inspection',
            'view_mode': 'list,form',
            'domain': [('picking_id', '=', self.id)],
            'context': {'default_picking_id': self.id}
        }

    def action_create_qc_inspection(self):
        """Create a new QC inspection from picking"""
        self.ensure_one()
        # Create QC inspection
        inspection = self.env['qc.inspection'].create({
            'product_id': self.move_ids_without_package[0].product_id.id if self.move_ids_without_package else False,
            'picking_id': self.id,
            'lot_id': self.move_ids_without_package[0].lot_ids[0].id if self.move_ids_without_package[
                0].lot_ids else False,
        })
        # Open the created inspection
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'qc.inspection',
            'res_id': inspection.id,
            'view_mode': 'form',
            'target': 'current',
        }