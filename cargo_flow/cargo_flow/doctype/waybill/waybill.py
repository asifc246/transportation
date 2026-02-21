import frappe
from frappe.model.document import Document
from frappe.utils import flt, now, add_days, today


class Waybill(Document):

    def validate(self):
        self._calc_total_charges()

    def on_submit(self):
        self.db_set("status", "Issued")
        if self.booking:
            frappe.db.set_value("Booking", self.booking, "status", "In Transit")

    def on_cancel(self):
        self.db_set("status", "Cancelled")

    # ------------------------------------------------------------------
    # Total charges
    # ------------------------------------------------------------------

    def _calc_total_charges(self):
        additional = sum(flt(r.amount) for r in self.additional_charges)
        self.total_charges = flt(self.freight_charges) + additional

    # ------------------------------------------------------------------
    # Confirm Dispatch
    # ------------------------------------------------------------------

    @frappe.whitelist()
    def confirm_dispatch(self):
        if self.docstatus != 1:
            frappe.throw("Submit the Waybill before confirming dispatch.")
        if self.status != "Issued":
            frappe.throw(f"Cannot dispatch a Waybill in status '{self.status}'.")

        self.db_set("status", "Dispatched")
        self.db_set("actual_pickup_datetime", now())

        if self.vehicle_allocation:
            frappe.db.set_value("Vehicle Allocation", self.vehicle_allocation, "status", "Dispatched")

        frappe.msgprint("Dispatch confirmed.", alert=True, indicator="blue")

    # ------------------------------------------------------------------
    # Confirm Delivery → auto-create Sales Invoice
    # ------------------------------------------------------------------

    @frappe.whitelist()
    def confirm_delivery(self, confirmed_by=None, remarks=None):
        if self.docstatus != 1:
            frappe.throw("Submit the Waybill before confirming delivery.")
        if self.status == "Delivered":
            frappe.throw("Delivery has already been confirmed for this Waybill.")

        self.db_set("delivery_confirmed", 1)
        self.db_set("delivery_confirmed_by", confirmed_by or "")
        self.db_set("delivery_remarks", remarks or "")
        self.db_set("actual_delivery_datetime", now())
        self.db_set("status", "Delivered")

        if self.booking:
            frappe.db.set_value("Booking", self.booking, "status", "Delivered")
        if self.vehicle_allocation:
            frappe.db.set_value("Vehicle Allocation", self.vehicle_allocation, "status", "Delivered")

        invoice_name = self._create_sales_invoice()
        self.db_set("invoice", invoice_name)

        frappe.msgprint(
            f"Delivery confirmed. Invoice <b>{invoice_name}</b> created automatically.",
            alert=True,
            indicator="green",
        )
        return invoice_name

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_company(self):
        company = frappe.defaults.get_global_default("company")
        if not company:
            frappe.throw(
                "No default company set. Please configure it in "
                "<b>Settings → System Settings</b>."
            )
        return company

    def _get_income_account(self, company):
        account = frappe.db.get_value("Company", company, "default_income_account")
        if account:
            return account
        account = frappe.db.get_value(
            "Account",
            {"company": company, "root_type": "Income", "is_group": 0},
            "name",
        )
        if account:
            return account
        frappe.throw(
            f"Could not find an Income Account for company <b>{company}</b>. "
            "Please set a <b>Default Income Account</b> in the Company master."
        )

    def _get_receivable_account(self, company):
        account = frappe.db.get_value("Company", company, "default_receivable_account")
        if account:
            return account
        account = frappe.db.get_value(
            "Account",
            {"company": company, "account_type": "Receivable", "is_group": 0},
            "name",
        )
        if account:
            return account
        frappe.throw(
            f"Could not find a Receivable Account for company <b>{company}</b>. "
            "Please set a <b>Default Receivable Account</b> in the Company master."
        )

    def _get_cost_center(self, company):
        return frappe.db.get_value("Company", company, "cost_center")

    def _get_price_list(self):
        price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
        return price_list or "Standard Selling"

    # ------------------------------------------------------------------
    # Sales Invoice builder
    # ------------------------------------------------------------------

    def _create_sales_invoice(self):
        company           = self._get_company()
        income_account    = self._get_income_account(company)
        receivable_account = self._get_receivable_account(company)
        cost_center       = self._get_cost_center(company)
        price_list        = self._get_price_list()
        currency          = self.currency or frappe.db.get_value("Company", company, "default_currency") or "USD"

        invoice                     = frappe.new_doc("Sales Invoice")
        invoice.company             = company
        invoice.customer            = self.customer
        invoice.currency            = currency
        invoice.conversion_rate     = 1.0
        invoice.selling_price_list  = price_list
        invoice.price_list_currency = currency
        invoice.plc_conversion_rate = 1.0
        invoice.debit_to            = receivable_account
        invoice.due_date            = add_days(today(), 30)
        invoice.po_no               = self.name
        invoice.remarks             = (
            f"Waybill: {self.name}  |  "
            f"Booking: {self.booking or '—'}  |  "
            f"Route: {self.origin} → {self.destination}"
        )

        def add_item(item_name, description, rate):
            rate = flt(rate)
            invoice.append("items", {
                "item_name":         str(item_name),
                "description":       str(description),
                "qty":               1.0,
                "rate":              rate,
                "amount":            rate,
                "net_rate":          rate,
                "net_amount":        rate,
                "base_rate":         rate,
                "base_amount":       rate,
                "base_net_rate":     rate,
                "base_net_amount":   rate,
                "uom":               "Nos",
                "stock_uom":         "Nos",
                "conversion_factor": 1.0,
                "income_account":    income_account,
                "cost_center":       cost_center,
            })

        # ── Freight line ───────────────────────────────────────────
        if flt(self.freight_charges):
            add_item(
                item_name=f"Freight – {self.origin} to {self.destination}",
                description=(
                    f"Service: {self.service_type or '—'} | "
                    f"Cargo: {self.cargo_type or '—'} | "
                    f"Weight: {flt(self.total_weight_kg)} KG"
                ),
                rate=self.freight_charges,
            )

        # ── Additional charge lines ────────────────────────────────
        for charge in self.additional_charges:
            if flt(charge.amount):
                add_item(
                    item_name=charge.charge_type,
                    description=charge.description or charge.charge_type,
                    rate=charge.amount,
                )

        if not invoice.items:
            frappe.throw(
                "Cannot create an invoice with no charges. "
                "Please add freight or additional charges to the Waybill."
            )

        # Set totals explicitly so ERPNext GL entries don't hit None * None
        total = sum(flt(i.rate) for i in invoice.items)
        invoice.total           = total
        invoice.net_total       = total
        invoice.grand_total     = total
        invoice.rounded_total   = total
        invoice.base_total      = total
        invoice.base_net_total  = total
        invoice.base_grand_total = total
        invoice.outstanding_amount = total

        # Only ignore permissions and other-app hooks — NOT validate/submit logic
        invoice.flags.ignore_permissions = True

        invoice.insert()
        invoice.submit()
        return invoice.name