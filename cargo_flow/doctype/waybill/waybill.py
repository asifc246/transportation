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
        """Mark waybill as Dispatched and stamp actual pickup time."""
        if self.docstatus != 1:
            frappe.throw("Submit the Waybill before confirming dispatch.")
        if self.status not in ("Issued",):
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
        """
        Confirm delivery and auto-create a submitted Sales Invoice.
        Returns the new invoice name.
        """
        if self.docstatus != 1:
            frappe.throw("Submit the Waybill before confirming delivery.")
        if self.status == "Delivered":
            frappe.throw("Delivery has already been confirmed for this Waybill.")

        # Stamp delivery info
        self.db_set("delivery_confirmed", 1)
        self.db_set("delivery_confirmed_by", confirmed_by or "")
        self.db_set("delivery_remarks", remarks or "")
        self.db_set("actual_delivery_datetime", now())
        self.db_set("status", "Delivered")

        # Cascade status updates
        if self.booking:
            frappe.db.set_value("Booking", self.booking, "status", "Delivered")
        if self.vehicle_allocation:
            frappe.db.set_value("Vehicle Allocation", self.vehicle_allocation, "status", "Delivered")

        # Auto-create invoice
        invoice_name = self._create_sales_invoice()
        self.db_set("invoice", invoice_name)

        frappe.msgprint(
            f"Delivery confirmed. Invoice <b>{invoice_name}</b> created automatically.",
            alert=True,
            indicator="green",
        )
        return invoice_name

    # ------------------------------------------------------------------
    # Sales Invoice builder
    # ------------------------------------------------------------------

    def _create_sales_invoice(self):
        """
        Build and submit a Sales Invoice from this Waybill.
        Line items are created for Freight Charges + each Additional Charge.
        """
        invoice = frappe.new_doc("Sales Invoice")
        invoice.customer    = self.customer
        invoice.currency    = self.currency or "USD"
        invoice.due_date    = add_days(today(), 30)
        invoice.po_no       = self.name          # Waybill ref as PO number
        invoice.remarks     = (
            f"Waybill: {self.name}  |  "
            f"Booking: {self.booking or '—'}  |  "
            f"Route: {self.origin} → {self.destination}"
        )

        # ── Freight line ───────────────────────────────────────────
        if flt(self.freight_charges):
            invoice.append("items", {
                "item_name":   f"Freight – {self.origin} to {self.destination}",
                "description": (
                    f"Service: {self.service_type or '—'} | "
                    f"Cargo: {self.cargo_type or '—'} | "
                    f"Weight: {self.total_weight_kg} KG | "
                    f"Rate type: {self.rate_type or '—'}"
                ),
                "qty":   1,
                "rate":  flt(self.freight_charges),
                "uom":   "Nos",
            })

        # ── Additional charge lines ────────────────────────────────
        for charge in self.additional_charges:
            invoice.append("items", {
                "item_name":   charge.charge_type,
                "description": charge.description or charge.charge_type,
                "qty":         1,
                "rate":        flt(charge.amount),
                "uom":         "Nos",
            })

        # Insert and submit
        invoice.flags.ignore_permissions = True
        invoice.insert()
        invoice.submit()
        return invoice.name
