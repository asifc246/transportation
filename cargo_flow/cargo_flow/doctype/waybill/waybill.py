# import frappe
# from frappe.model.document import Document
# from frappe.utils import flt, now, add_days, today


# class Waybill(Document):

#     def validate(self):
#         self._calc_total_charges()

#     def on_submit(self):
#         self.db_set("status", "Issued")
#         if self.booking:
#             frappe.db.set_value("Booking", self.booking, "status", "In Transit")

#     def on_cancel(self):
#         self.db_set("status", "Cancelled")

#     # ------------------------------------------------------------------
#     # Total charges
#     # ------------------------------------------------------------------

#     def _calc_total_charges(self):
#         additional = sum(flt(r.amount) for r in self.additional_charges)
#         self.total_charges = flt(self.freight_charges) + additional

#     # ------------------------------------------------------------------
#     # Confirm Dispatch
#     # ------------------------------------------------------------------

#     @frappe.whitelist()
#     def confirm_dispatch(self):
#         if self.docstatus != 1:
#             frappe.throw("Submit the Waybill before confirming dispatch.")
#         if self.status != "Issued":
#             frappe.throw(f"Cannot dispatch a Waybill in status '{self.status}'.")

#         self.db_set("status", "Dispatched")
#         self.db_set("actual_pickup_datetime", now())

#         if self.vehicle_allocation:
#             frappe.db.set_value("Vehicle Allocation", self.vehicle_allocation, "status", "Dispatched")

#         frappe.msgprint("Dispatch confirmed.", alert=True, indicator="blue")

#     # ------------------------------------------------------------------
#     # Confirm Delivery → auto-create Sales Invoice
#     # ------------------------------------------------------------------

#     @frappe.whitelist()
#     def confirm_delivery(self, confirmed_by=None, remarks=None):
#         if self.docstatus != 1:
#             frappe.throw("Submit the Waybill before confirming delivery.")
#         if self.status == "Delivered":
#             frappe.throw("Delivery has already been confirmed for this Waybill.")

#         self.db_set("delivery_confirmed", 1)
#         self.db_set("delivery_confirmed_by", confirmed_by or "")
#         self.db_set("delivery_remarks", remarks or "")
#         self.db_set("actual_delivery_datetime", now())
#         self.db_set("status", "Delivered")

#         if self.booking:
#             frappe.db.set_value("Booking", self.booking, "status", "Delivered")
#         if self.vehicle_allocation:
#             frappe.db.set_value("Vehicle Allocation", self.vehicle_allocation, "status", "Delivered")

#         invoice_name = self._create_sales_invoice()
#         self.db_set("invoice", invoice_name)

#         frappe.msgprint(
#             f"Delivery confirmed. Invoice <b>{invoice_name}</b> created automatically.",
#             alert=True,
#             indicator="green",
#         )
#         return invoice_name

#     # ------------------------------------------------------------------
#     # Helpers
#     # ------------------------------------------------------------------

#     def _get_company(self):
#         company = frappe.defaults.get_global_default("company")
#         if not company:
#             frappe.throw(
#                 "No default company set. Please configure it in "
#                 "<b>Settings → System Settings</b>."
#             )
#         return company

#     def _get_income_account(self, company):
#         account = frappe.db.get_value("Company", company, "default_income_account")
#         if account:
#             return account
#         account = frappe.db.get_value(
#             "Account",
#             {"company": company, "root_type": "Income", "is_group": 0},
#             "name",
#         )
#         if account:
#             return account
#         frappe.throw(
#             f"Could not find an Income Account for company <b>{company}</b>. "
#             "Please set a <b>Default Income Account</b> in the Company master."
#         )

#     def _get_receivable_account(self, company):
#         account = frappe.db.get_value("Company", company, "default_receivable_account")
#         if account:
#             return account
#         account = frappe.db.get_value(
#             "Account",
#             {"company": company, "account_type": "Receivable", "is_group": 0},
#             "name",
#         )
#         if account:
#             return account
#         frappe.throw(
#             f"Could not find a Receivable Account for company <b>{company}</b>. "
#             "Please set a <b>Default Receivable Account</b> in the Company master."
#         )

#     def _get_cost_center(self, company):
#         return frappe.db.get_value("Company", company, "cost_center")

#     def _get_price_list(self):
#         price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
#         return price_list or "Standard Selling"

#     # ------------------------------------------------------------------
#     # Sales Invoice builder
#     # ------------------------------------------------------------------

#     def _create_sales_invoice(self):
#         company           = self._get_company()
#         income_account    = self._get_income_account(company)
#         receivable_account = self._get_receivable_account(company)
#         cost_center       = self._get_cost_center(company)
#         price_list        = self._get_price_list()
#         currency          = self.currency or frappe.db.get_value("Company", company, "default_currency") or "USD"

#         invoice                     = frappe.new_doc("Sales Invoice")
#         invoice.company             = company
#         invoice.customer            = self.customer
#         invoice.currency            = currency
#         invoice.conversion_rate     = 1.0
#         invoice.selling_price_list  = price_list
#         invoice.price_list_currency = currency
#         invoice.plc_conversion_rate = 1.0
#         invoice.debit_to            = receivable_account
#         invoice.due_date            = add_days(today(), 30)
#         invoice.po_no               = self.name
#         invoice.remarks             = (
#             f"Waybill: {self.name}  |  "
#             f"Booking: {self.booking or '—'}  |  "
#             f"Route: {self.origin} → {self.destination}"
#         )

#         def add_item(item_name, description, rate):
#             rate = flt(rate)
#             invoice.append("items", {
#                 "item_name":         str(item_name),
#                 "description":       str(description),
#                 "qty":               1.0,
#                 "rate":              rate,
#                 "amount":            rate,
#                 "net_rate":          rate,
#                 "net_amount":        rate,
#                 "base_rate":         rate,
#                 "base_amount":       rate,
#                 "base_net_rate":     rate,
#                 "base_net_amount":   rate,
#                 "uom":               "Nos",
#                 "stock_uom":         "Nos",
#                 "conversion_factor": 1.0,
#                 "income_account":    income_account,
#                 "cost_center":       cost_center,
#             })

#         # ── Freight line ───────────────────────────────────────────
#         if flt(self.freight_charges):
#             add_item(
#                 item_name=f"Freight – {self.origin} to {self.destination}",
#                 description=(
#                     f"Service: {self.service_type or '—'} | "
#                     f"Cargo: {self.cargo_type or '—'} | "
#                     f"Weight: {flt(self.total_weight_kg)} KG"
#                 ),
#                 rate=self.freight_charges,
#             )

#         # ── Additional charge lines ────────────────────────────────
#         for charge in self.additional_charges:
#             if flt(charge.amount):
#                 add_item(
#                     item_name=charge.charge_type,
#                     description=charge.description or charge.charge_type,
#                     rate=charge.amount,
#                 )

#         if not invoice.items:
#             frappe.throw(
#                 "Cannot create an invoice with no charges. "
#                 "Please add freight or additional charges to the Waybill."
#             )

#         # Set totals explicitly so ERPNext GL entries don't hit None * None
#         total = sum(flt(i.rate) for i in invoice.items)
#         invoice.total           = total
#         invoice.net_total       = total
#         invoice.grand_total     = total
#         invoice.rounded_total   = total
#         invoice.base_total      = total
#         invoice.base_net_total  = total
#         invoice.base_grand_total = total
#         invoice.outstanding_amount = total

#         # Only ignore permissions and other-app hooks — NOT validate/submit logic
#         invoice.flags.ignore_permissions = True

#         invoice.insert()
#         invoice.submit()
#         return invoice.name


import frappe
from frappe.model.document import Document
from frappe.utils import flt, now, add_days, today


class Waybill(Document):

    def validate(self):
        self._calc_total_charges()
        self._calc_total_expenses()
        self._set_default_suppliers()

    def on_submit(self):
        self.db_set("status", "Issued")
        if self.booking:
            frappe.db.set_value("Booking", self.booking, "status", "In Transit")

    def on_cancel(self):
        self.db_set("status", "Cancelled")

    # ------------------------------------------------------------------
    # Calculations
    # ------------------------------------------------------------------

    def _calc_total_charges(self):
        additional = sum(flt(r.amount) for r in self.additional_charges)
        self.total_charges = flt(self.freight_charges) + additional

    def _calc_total_expenses(self):
        self.total_expenses = sum(flt(r.amount) for r in self.expenses)

    def _set_default_suppliers(self):
        """
        For each expense row that has a vehicle but no supplier set,
        default the supplier to that vehicle's rental provider.
        """
        for row in self.expenses:
            if not row.supplier and row.vehicle:
                provider = frappe.db.get_value(
                    "Vehicle", row.vehicle, "cf_rental_provider"
                )
                if provider:
                    row.supplier = provider

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
            frappe.db.set_value(
                "Vehicle Allocation", self.vehicle_allocation, "status", "Dispatched"
            )
        frappe.msgprint("Dispatch confirmed.", alert=True, indicator="blue")

    # ------------------------------------------------------------------
    # Confirm Delivery → auto Sales Invoice
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
            frappe.db.set_value(
                "Vehicle Allocation", self.vehicle_allocation, "status", "Delivered"
            )

        invoice_name = self._create_sales_invoice()
        self.db_set("invoice", invoice_name)

        frappe.msgprint(
            f"Delivery confirmed. Invoice <b>{invoice_name}</b> created automatically.",
            alert=True,
            indicator="green",
        )
        return invoice_name

    # ------------------------------------------------------------------
    # Generate Purchase Invoice from expenses
    # ------------------------------------------------------------------

    @frappe.whitelist()
    def generate_purchase_invoice(self, supplier=None):
        """
        Create one Purchase Invoice for all expenses on this Waybill.
        Supplier priority: argument → most common supplier in rows → rental provider.
        Returns the Purchase Invoice name.
        """
        if self.docstatus != 1:
            frappe.throw("Submit the Waybill before generating a Purchase Invoice.")

        if self.purchase_invoice:
            frappe.throw(
                f"Purchase Invoice <b>{self.purchase_invoice}</b> already exists "
                "for this Waybill."
            )

        if not self.expenses:
            frappe.throw(
                "No expenses found on this Waybill. "
                "Please add expenses before generating a Purchase Invoice."
            )

        supplier = supplier or self._resolve_supplier()
        if not supplier:
            frappe.throw(
                "Could not determine a supplier. Please set a supplier on at least "
                "one expense row or add a Rental Provider to the vehicle."
            )

        pi_name = self._create_purchase_invoice(supplier)
        self.db_set("purchase_invoice", pi_name)

        frappe.msgprint(
            f"Purchase Invoice <b>{pi_name}</b> created successfully.",
            alert=True,
            indicator="green",
        )
        return pi_name

    def _resolve_supplier(self):
        """Pick the best supplier: most frequent in expense rows, else rental provider."""
        suppliers = [r.supplier for r in self.expenses if r.supplier]
        if suppliers:
            return max(set(suppliers), key=suppliers.count)

        # Fallback: get rental provider from any vehicle in allocation
        if self.vehicle_allocation:
            rows = frappe.get_all(
                "Vehicle Allocation Item",
                filters={"parent": self.vehicle_allocation},
                fields=["vehicle"],
                limit=1,
            )
            if rows and rows[0].vehicle:
                return frappe.db.get_value(
                    "Vehicle", rows[0].vehicle, "cf_rental_provider"
                )
        return None

    def _create_purchase_invoice(self, supplier):
        company          = self._get_company()
        expense_account  = self._get_expense_account(company)
        cost_center      = self._get_cost_center(company)
        currency         = self.currency or frappe.db.get_value(
            "Company", company, "default_currency"
        ) or "USD"

        pi               = frappe.new_doc("Purchase Invoice")
        pi.company       = company
        pi.supplier      = supplier
        pi.currency      = currency
        pi.conversion_rate      = 1.0
        pi.plc_conversion_rate  = 1.0
        pi.buying_price_list    = (
            frappe.db.get_single_value("Buying Settings", "buying_price_list")
            or "Standard Buying"
        )
        pi.due_date      = add_days(today(), 30)
        pi.bill_no       = self.name
        pi.remarks       = (
            f"Expenses for Waybill: {self.name}  |  "
            f"Booking: {self.booking or '—'}  |  "
            f"Route: {self.origin} → {self.destination}"
        )

        def add_item(item_name, description, rate):
            rate = flt(rate)
            pi.append("items", {
                "item_name":         str(item_name),
                "description":       str(description or item_name),
                "qty":               1.0,
                "rate":              rate,
                "amount":            rate,
                "base_rate":         rate,
                "base_amount":       rate,
                "net_rate":          rate,
                "net_amount":        rate,
                "base_net_rate":     rate,
                "base_net_amount":   rate,
                "uom":               "Nos",
                "stock_uom":         "Nos",
                "conversion_factor": 1.0,
                "expense_account":   expense_account,
                "cost_center":       cost_center,
            })

        for row in self.expenses:
            if flt(row.amount):
                label = row.expense_type
                if row.vehicle:
                    label += f" – {row.vehicle}"
                add_item(
                    item_name=label,
                    description=row.description or label,
                    rate=row.amount,
                )

        if not pi.items:
            frappe.throw("No expense rows with a valid amount found.")

        total = sum(flt(i.rate) for i in pi.items)
        pi.total             = total
        pi.net_total         = total
        pi.grand_total       = total
        pi.rounded_total     = total
        pi.base_total        = total
        pi.base_net_total    = total
        pi.base_grand_total  = total
        pi.outstanding_amount = total

        pi.flags.ignore_permissions = True
        pi.insert()
        pi.submit()
        return pi.name

    # ------------------------------------------------------------------
    # Sales Invoice helpers
    # ------------------------------------------------------------------

    def _get_company(self):
        company = frappe.defaults.get_global_default("company")
        if not company:
            frappe.throw(
                "No default company set. Configure it in "
                "<b>Settings → System Settings</b>."
            )
        return company

    def _get_income_account(self, company):
        acct = frappe.db.get_value("Company", company, "default_income_account")
        if acct:
            return acct
        acct = frappe.db.get_value(
            "Account",
            {"company": company, "root_type": "Income", "is_group": 0},
            "name",
        )
        if acct:
            return acct
        frappe.throw(
            f"No Income Account found for <b>{company}</b>. "
            "Set <b>Default Income Account</b> in Company master."
        )

    def _get_expense_account(self, company):
        acct = frappe.db.get_value("Company", company, "default_expense_account")
        if acct:
            return acct
        acct = frappe.db.get_value(
            "Account",
            {"company": company, "root_type": "Expense", "is_group": 0},
            "name",
        )
        if acct:
            return acct
        frappe.throw(
            f"No Expense Account found for <b>{company}</b>. "
            "Set <b>Default Expense Account</b> in Company master."
        )

    def _get_receivable_account(self, company):
        acct = frappe.db.get_value("Company", company, "default_receivable_account")
        if acct:
            return acct
        acct = frappe.db.get_value(
            "Account",
            {"company": company, "account_type": "Receivable", "is_group": 0},
            "name",
        )
        if acct:
            return acct
        frappe.throw(
            f"No Receivable Account found for <b>{company}</b>. "
            "Set <b>Default Receivable Account</b> in Company master."
        )

    def _get_cost_center(self, company):
        return frappe.db.get_value("Company", company, "cost_center")

    def _get_price_list(self):
        return (
            frappe.db.get_single_value("Selling Settings", "selling_price_list")
            or "Standard Selling"
        )

    def _create_sales_invoice(self):
        company            = self._get_company()
        income_account     = self._get_income_account(company)
        receivable_account = self._get_receivable_account(company)
        cost_center        = self._get_cost_center(company)
        price_list         = self._get_price_list()
        currency           = self.currency or frappe.db.get_value(
            "Company", company, "default_currency"
        ) or "USD"

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
                "Add freight or additional charges to the Waybill."
            )

        total = sum(flt(i.rate) for i in invoice.items)
        invoice.total              = total
        invoice.net_total          = total
        invoice.grand_total        = total
        invoice.rounded_total      = total
        invoice.base_total         = total
        invoice.base_net_total     = total
        invoice.base_grand_total   = total
        invoice.outstanding_amount = total

        invoice.flags.ignore_permissions = True
        invoice.insert()
        invoice.submit()
        return invoice.name
