import logging
from datetime import datetime, timedelta

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class QCDashboardController(http.Controller):

    @http.route("/qc/dashboard", type="http", auth="user", website=False)
    def qc_dashboard(self, **kwargs):
        """Main QC Dashboard"""
        try:
            _logger.info("QC Dashboard accessed by user: %s", request.env.user.name)

            # Use Odoo's timezone-aware dates
            today = fields.Date.context_today(request.env["qc.inspection"])
            week_ago = today - timedelta(days=7)
            month_ago = today - timedelta(days=30)

            # Today's stats - use proper datetime conversion
            today_start = fields.Datetime.to_string(
                datetime.combine(today, datetime.min.time())
            )
            today_end = fields.Datetime.to_string(
                datetime.combine(today, datetime.max.time())
            )

            today_inspections = request.env["qc.inspection"].search(
                [
                    ("inspection_date", ">=", today_start),
                    ("inspection_date", "<=", today_end),
                ]
            )

            today_total = len(today_inspections)
            today_pending = len(
                today_inspections.filtered(
                    lambda x: x.state in ["draft", "in_progress"]
                )
            )
            today_passed = len(today_inspections.filtered(lambda x: x.state == "pass"))
            today_failed = len(today_inspections.filtered(lambda x: x.state == "fail"))

            # Week stats
            week_start = fields.Datetime.to_string(
                datetime.combine(week_ago, datetime.min.time())
            )
            week_inspections = request.env["qc.inspection"].search(
                [("inspection_date", ">=", week_start)]
            )
            week_total = len(week_inspections)
            week_passed = len(week_inspections.filtered(lambda x: x.state == "pass"))
            week_pass_rate = (
                round((week_passed / week_total * 100), 1) if week_total > 0 else 0
            )

            # Month stats
            month_start = fields.Datetime.to_string(
                datetime.combine(month_ago, datetime.min.time())
            )
            month_inspections = request.env["qc.inspection"].search(
                [("inspection_date", ">=", month_start)]
            )
            month_total = len(month_inspections)
            month_passed = len(month_inspections.filtered(lambda x: x.state == "pass"))
            month_pass_rate = (
                round((month_passed / month_total * 100), 1) if month_total > 0 else 0
            )

            # Recent failures
            recent_failures = request.env["qc.inspection"].search(
                [("state", "=", "fail")], order="inspection_date desc", limit=5
            )

            # Debug log
            _logger.info(
                "Dashboard Data - Today: %s, Week: %s, Month: %s",
                today_total,
                week_total,
                month_total,
            )

            values = {
                "today_total": today_total,
                "today_pending": today_pending,
                "today_passed": today_passed,
                "today_failed": today_failed,
                "week_total": week_total,
                "week_passed": week_passed,
                "week_pass_rate": week_pass_rate,
                "month_total": month_total,
                "month_passed": month_passed,
                "month_pass_rate": month_pass_rate,
                "recent_failures": recent_failures,
            }

            return request.render("smart_inventory_qc.qc_dashboard_template", values)

        except Exception as e:
            _logger.error("Dashboard error: %s", str(e))
            return f"<h1>Dashboard Error</h1><p>{str(e)}</p>"
