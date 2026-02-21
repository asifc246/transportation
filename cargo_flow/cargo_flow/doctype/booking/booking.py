import frappe
from frappe.model.document import Document
from frappe.utils import flt


class Booking(Document):

    def validate(self):
        self.calculate_estimated_amount()

    def on_submit(self):
        self.db_set("status", "Confirmed")

    def on_cancel(self):
        self.db_set("status", "Cancelled")

    # ------------------------------------------------------------------
    # Estimated Amount
    # ------------------------------------------------------------------

    def calculate_estimated_amount(self):
        """Compute estimated_amount based on rate_type."""
        rate = flt(self.base_rate)
        if not rate:
            self.estimated_amount = 0
            return

        if self.rate_type == "Fixed":
            self.estimated_amount = rate
        elif self.rate_type == "Per KG":
            self.estimated_amount = rate * flt(self.total_weight_kg)
        elif self.rate_type == "Per CBM":
            self.estimated_amount = rate * flt(self.total_volume_cbm)
        elif self.rate_type == "Per Package":
            self.estimated_amount = rate * flt(self.no_of_packages)
        else:
            self.estimated_amount = 0

    # ------------------------------------------------------------------
    # Create Vehicle Allocation
    # ------------------------------------------------------------------

    @frappe.whitelist()
    def create_vehicle_allocation(self):
        """
        Create a Vehicle Allocation document linked to this Booking.
        Can only be called once per booking.
        """
        if self.docstatus != 1:
            frappe.throw("Please submit the Booking before creating a Vehicle Allocation.")

        if self.vehicle_allocation:
            frappe.throw(
                f"Vehicle Allocation <b>{self.vehicle_allocation}</b> already exists "
                "for this booking."
            )

        allocation = frappe.new_doc("Vehicle Allocation")
        allocation.booking               = self.name
        allocation.customer              = self.customer
        allocation.customer_name         = self.customer_name
        allocation.origin                = self.origin
        allocation.origin_address        = self.origin_address
        allocation.destination           = self.destination
        allocation.destination_address   = self.destination_address
        allocation.expected_pickup_date  = self.expected_pickup_date
        allocation.expected_delivery_date = self.expected_delivery_date
        allocation.cargo_type            = self.cargo_type
        allocation.cargo_description     = self.cargo_description
        allocation.total_weight_kg       = self.total_weight_kg
        allocation.total_volume_cbm      = self.total_volume_cbm
        allocation.no_of_packages        = self.no_of_packages
        allocation.special_instructions  = self.special_instructions
        allocation.insert()

        self.db_set("vehicle_allocation", allocation.name)
        self.db_set("status", "Allocated")

        frappe.msgprint(
            f"Vehicle Allocation <b>{allocation.name}</b> created successfully.",
            alert=True,
            indicator="green",
        )
        return allocation.name
