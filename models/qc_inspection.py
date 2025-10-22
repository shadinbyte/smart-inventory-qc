from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class QCInspection(models.Model):
    _name = "qc.inspection"
    _description = "Quality Control Inspection"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "inspection_date desc, id desc"

    name = fields.Char(
        string="Reference", default="New", readonly=True, copy=False, tracking=True
    )

    product_id = fields.Many2one(
        "product.product", string="Product", required=True, tracking=True
    )

    lot_id = fields.Many2one("stock.lot", string="Lot/Serial Number", tracking=True)

    inspector_id = fields.Many2one(
        "res.users",
        string="Inspector",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )

    inspection_date = fields.Datetime(
        string="Inspection Date",
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )

    expected_date = fields.Datetime(string="Expected Completion", tracking=True)

    picking_id = fields.Many2one("stock.picking", string="Source Transfer", copy=False)

    partner_id = fields.Many2one(
        "res.partner",
        string="Supplier",
        related="picking_id.partner_id",
        store=True,
        tracking=True,
    )

    notes = fields.Text(string="Inspection Notes", tracking=True)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("pass", "Passed"),
            ("fail", "Failed"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )

    quantity_to_inspect = fields.Float(
        string="Quantity to Inspect",
        digits="Product Unit of Measure",
        required=True,
        default=1.0,
    )

    quantity_accepted = fields.Float(
        string="Quantity Accepted", digits="Product Unit of Measure", default=0.0
    )

    quantity_rejected = fields.Float(
        string="Quantity Rejected", digits="Product Unit of Measure", default=0.0
    )

    pass_rate = fields.Float(
        string="Pass Rate %", compute="_compute_pass_rate", store=True, tracking=True
    )

    quality_rating = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Good"),
            ("fair", "Fair"),
            ("poor", "Poor"),
        ],
        compute="_compute_quality_rating",
        store=True,
    )

    checklist_ids = fields.One2many(
        "qc.inspection.line", "inspection_id", string="Inspection Checklist"
    )

    checklist_progress = fields.Float(
        string="Checklist Progress", compute="_compute_checklist_progress"
    )

    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )

    _sql_constraints = [
        (
            "quantity_positive",
            "CHECK(quantity_to_inspect > 0)",
            "Quantity to inspect must be positive!",
        ),
    ]

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = (
                self.env["ir.sequence"].next_by_code("qc.inspection") or "New"
            )
        return super().create(vals)

    @api.depends("quantity_to_inspect", "quantity_accepted", "quantity_rejected")
    def _compute_pass_rate(self):
        for record in self:
            if record.quantity_to_inspect > 0:
                record.pass_rate = (
                    record.quantity_accepted / record.quantity_to_inspect
                ) * 100
            else:
                record.pass_rate = 0.0

    @api.depends("pass_rate")
    def _compute_quality_rating(self):
        for record in self:
            if record.pass_rate >= 90:
                record.quality_rating = "excellent"
            elif record.pass_rate >= 70:
                record.quality_rating = "good"
            elif record.pass_rate >= 50:
                record.quality_rating = "fair"
            else:
                record.quality_rating = "poor"

    @api.depends("checklist_ids", "checklist_ids.result")
    def _compute_checklist_progress(self):
        for record in self:
            total = len(record.checklist_ids)
            if total > 0:
                completed = len(
                    record.checklist_ids.filtered(
                        lambda x: x.result in ["pass", "fail"]
                    )
                )
                record.checklist_progress = (completed / total) * 100
            else:
                record.checklist_progress = 0.0

    @api.constrains("quantity_accepted", "quantity_rejected", "quantity_to_inspect")
    def _check_quantities(self):
        for record in self:
            total = record.quantity_accepted + record.quantity_rejected
            if total > record.quantity_to_inspect:
                raise ValidationError(
                    "Accepted + Rejected quantities cannot exceed the quantity to inspect!"
                )
            if record.quantity_accepted < 0 or record.quantity_rejected < 0:
                raise ValidationError("Quantities cannot be negative!")

    @api.constrains("picking_id", "product_id")
    def _check_unique_inspection(self):
        for record in self:
            if record.picking_id and record.product_id:
                existing = self.search(
                    [
                        ("picking_id", "=", record.picking_id.id),
                        ("product_id", "=", record.product_id.id),
                        ("id", "!=", record.id),
                        ("state", "!=", "cancel"),
                    ]
                )
                if existing:
                    raise ValidationError(
                        f"Active QC inspection already exists for {record.product_id.name} "
                        f"in transfer {record.picking_id.name}"
                    )

    def action_start_inspection(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError("Only draft inspections can be started!")
        self.state = "in_progress"
        self.message_post(body="Inspection started")

    def action_pass(self):
        self.ensure_one()
        if self.state != "in_progress":
            raise UserError("Only in-progress inspections can be passed!")

        if self.quantity_accepted == 0:
            self.quantity_accepted = self.quantity_to_inspect

        self.state = "pass"
        self.message_post(
            body=f"✅ Inspection PASSED - {self.pass_rate:.1f}% pass rate"
        )
        self._send_notification_email()

    def action_fail(self):
        self.ensure_one()
        if self.state != "in_progress":
            raise UserError("Only in-progress inspections can be failed!")

        if self.quantity_rejected == 0:
            self.quantity_rejected = self.quantity_to_inspect

        self.state = "fail"
        self.message_post(
            body=f"❌ Inspection FAILED - {self.pass_rate:.1f}% pass rate"
        )
        self._send_notification_email()
        self._create_quality_alert()

    def action_cancel(self):
        self.ensure_one()
        if self.state in ["pass", "fail"]:
            raise UserError("Cannot cancel completed inspections!")
        self.state = "cancel"
        self.message_post(body="Inspection cancelled")

    def action_reset_to_draft(self):
        self.ensure_one()
        if not self.env.user.has_group("smart_inventory_qc.group_qc_manager"):
            raise UserError("Only QC Managers can reset inspections!")
        self.state = "draft"
        self.message_post(body="Inspection reset to draft")

    def _send_notification_email(self):
        template = self.env.ref(
            "smart_inventory_qc.email_qc_result", raise_if_not_found=False
        )
        if template and self.partner_id:
            template.send_mail(self.id, force_send=True)

    def _create_quality_alert(self):
        if self.picking_id and self.partner_id:
            self.env["mail.activity"].create(
                {
                    "res_id": self.picking_id.id,
                    "res_model_id": self.env["ir.model"]._get("stock.picking").id,
                    "activity_type_id": self.env.ref(
                        "mail.mail_activity_data_warning"
                    ).id,
                    "summary": f"QC Failed: {self.product_id.name}",
                    "note": f"Quality inspection failed with {self.pass_rate:.1f}% pass rate.<br/>"
                    f"Rejected quantity: {self.quantity_rejected}<br/>"
                    f"Inspection: {self.name}",
                    "user_id": self.picking_id.user_id.id or self.env.user.id,
                }
            )

    @api.model
    def cron_auto_create_incoming_qc(self):
        try:
            pickings = self.env["stock.picking"].search(
                [
                    ("picking_type_code", "=", "incoming"),
                    ("state", "in", ["assigned", "confirmed"]),
                    ("qc_inspection_count", "=", 0),
                ],
                limit=50,
            )

            for picking in pickings:
                for move in picking.move_ids_without_package:
                    if not move.product_id:
                        continue

                    existing = self.search(
                        [
                            ("picking_id", "=", picking.id),
                            ("product_id", "=", move.product_id.id),
                            ("state", "!=", "cancel"),
                        ]
                    )

                    if not existing:
                        self.create(
                            {
                                "product_id": move.product_id.id,
                                "picking_id": picking.id,
                                "quantity_to_inspect": move.product_uom_qty,
                                "lot_id": move.lot_ids[0].id if move.lot_ids else False,
                            }
                        )
        except Exception as e:
            self.env["ir.logging"].sudo().create(
                {
                    "name": "QC Auto-creation Error",
                    "type": "server",
                    "level": "error",
                    "message": str(e),
                    "path": "smart_inventory_qc.cron",
                    "func": "cron_auto_create_incoming_qc",
                }
            )


class QCInspectionLine(models.Model):
    _name = "qc.inspection.line"
    _description = "QC Inspection Checklist Line"
    _order = "sequence, id"

    inspection_id = fields.Many2one(
        "qc.inspection", string="Inspection", required=True, ondelete="cascade"
    )

    sequence = fields.Integer(default=10)

    name = fields.Char(string="Checkpoint", required=True)

    description = fields.Text(string="Description")

    result = fields.Selection(
        [
            ("pass", "Pass"),
            ("fail", "Fail"),
            ("na", "N/A"),
        ],
        string="Result",
    )

    remarks = fields.Text(string="Remarks")
