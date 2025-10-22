from odoo import api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    qc_inspection_ids = fields.One2many(
        "qc.inspection", "picking_id", string="QC Inspections"
    )

    qc_inspection_count = fields.Integer(string="QC Count", compute="_compute_qc_count")

    qc_status = fields.Selection(
        [
            ("none", "No QC Required"),
            ("pending", "QC Pending"),
            ("in_progress", "QC In Progress"),
            ("passed", "QC Passed"),
            ("failed", "QC Failed"),
        ],
        compute="_compute_qc_status",
        string="QC Status",
        store=True,
    )

    require_qc = fields.Boolean(
        string="Require QC", compute="_compute_require_qc", store=True
    )

    @api.depends("qc_inspection_ids")
    def _compute_qc_count(self):
        for record in self:
            record.qc_inspection_count = len(record.qc_inspection_ids)

    @api.depends("picking_type_code")
    def _compute_require_qc(self):
        for record in self:
            record.require_qc = record.picking_type_code == "incoming"

    @api.depends("qc_inspection_ids", "qc_inspection_ids.state")
    def _compute_qc_status(self):
        for record in self:
            if not record.require_qc or not record.qc_inspection_ids:
                record.qc_status = "none"
                continue

            states = record.qc_inspection_ids.mapped("state")

            if "fail" in states:
                record.qc_status = "failed"
            elif all(s == "pass" for s in states):
                record.qc_status = "passed"
            elif any(s == "in_progress" for s in states):
                record.qc_status = "in_progress"
            else:
                record.qc_status = "pending"

    def action_view_qc_inspections(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "QC Inspections",
            "res_model": "qc.inspection",
            "view_mode": "list,form",
            "domain": [("picking_id", "=", self.id)],
            "context": {
                "default_picking_id": self.id,
                "default_product_id": (
                    self.move_ids_without_package[0].product_id.id
                    if self.move_ids_without_package
                    else False
                ),
                "default_quantity_to_inspect": (
                    self.move_ids_without_package[0].product_uom_qty
                    if self.move_ids_without_package
                    else 1.0
                ),
            },
        }

    def action_create_qc_inspection(self):
        self.ensure_one()

        if not self.move_ids_without_package:
            raise UserError("No products found in this transfer!")

        inspections_created = []

        for move in self.move_ids_without_package:
            if not move.product_id:
                continue

            existing = self.env["qc.inspection"].search(
                [
                    ("picking_id", "=", self.id),
                    ("product_id", "=", move.product_id.id),
                    ("state", "!=", "cancel"),
                ]
            )

            if existing:
                continue

            inspection = self.env["qc.inspection"].create(
                {
                    "product_id": move.product_id.id,
                    "picking_id": self.id,
                    "quantity_to_inspect": move.product_uom_qty,
                    "lot_id": move.lot_ids[0].id if move.lot_ids else False,
                }
            )
            inspections_created.append(inspection.id)

        if not inspections_created:
            raise UserError(
                "QC inspections already exist for all products in this transfer!"
            )

        if len(inspections_created) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "qc.inspection",
                "res_id": inspections_created[0],
                "view_mode": "form",
                "target": "current",
            }
        else:
            return {
                "type": "ir.actions.act_window",
                "name": "QC Inspections Created",
                "res_model": "qc.inspection",
                "view_mode": "list,form",
                "domain": [("id", "in", inspections_created)],
                "target": "current",
            }

    def button_validate(self):
        for picking in self:
            if picking.require_qc and picking.qc_status in ["pending", "in_progress"]:
                raise UserError(
                    f"Cannot validate transfer {picking.name}!\n"
                    f"Quality inspections are {picking.qc_status}. "
                    f"Complete all QC inspections first."
                )

            if picking.qc_status == "failed":
                raise UserError(
                    f"Cannot validate transfer {picking.name}!\n"
                    f"Some quality inspections have failed. "
                    f"Review failed inspections before proceeding."
                )

        return super().button_validate()
