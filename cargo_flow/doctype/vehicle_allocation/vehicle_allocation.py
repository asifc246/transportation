import frappe
from frappe.model.document import Document
from frappe.utils import flt, today


class VehicleAllocation(Document):

    def validate(self):
        self._warn_weight_mismatch()

    def on_submit(self):
        self.db_set("status", "Confirmed")
        if self.booking:
            frappe.db.set_value("Booking", self.booking, "status", "Allocated")

    def on_cancel(self):
        self.db_set("status", "Cancelled")
        if self.booking:
            booking_status = frappe.db.get_value("Booking", self.booking, "status")
            if booking_status == "Allocated":
                frappe.db.set_value("Booking", self.booking, "status", "Confirmed")

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _warn_weight_mismatch(self):
        total_assigned = sum(flt(r.assigned_weight_kg) for r in self.vehicles)
        if total_assigned and flt(self.total_weight_kg):
            if total_assigned > flt(self.total_weight_kg) * 1.05:   # 5% tolerance
                frappe.msgprint(
                    f"Assigned weight ({total_assigned:.2f} KG) exceeds booking cargo "
                    f"weight ({self.total_weight_kg:.2f} KG) by more than 5%.",
                    indicator="orange",
                    title="Weight Warning",
                )

    # ------------------------------------------------------------------
    # Create Waybill(s)
    # ------------------------------------------------------------------

    @frappe.whitelist()
    def create_waybill(self):
        """
        Create one or more Waybill documents from this Vehicle Allocation.
        Scope is controlled by self.waybill_scope:
          • 'All Vehicles (Single Waybill)' → one Waybill, all vehicles listed
          • 'Each Vehicle (Separate Waybills)' → one Waybill per vehicle row
        Returns a list of created Waybill names.
        """
        if self.docstatus != 1:
            frappe.throw("Submit the Vehicle Allocation before creating Waybills.")

        booking = frappe.get_doc("Booking", self.booking)
        created = []

        if self.waybill_scope == "All Vehicles (Single Waybill)":
            wb = self._build_waybill(booking, self.vehicles)
            wb.insert()
            created.append(wb.name)
        else:
            for row in self.vehicles:
                wb = self._build_waybill(booking, [row])
                wb.insert()
                created.append(wb.name)

        # Update waybill counters
        self.db_set("waybill_count", flt(self.waybill_count) + len(created))
        frappe.db.set_value(
            "Booking", self.booking, "waybill_count",
            flt(booking.waybill_count) + len(created),
        )

        frappe.msgprint(
            f"{len(created)} Waybill(s) created: <b>{', '.join(created)}</b>",
            alert=True,
            indicator="green",
        )
        return created

    def _build_waybill(self, booking, vehicle_rows):
        """Construct an unsaved Waybill doc."""
        wb = frappe.new_doc("Waybill")

        # References
        wb.booking            = booking.name
        wb.vehicle_allocation = self.name
        wb.waybill_date       = today()

        # Customer
        wb.customer           = booking.customer
        wb.customer_name      = booking.customer_name
        wb.contact_person     = booking.contact_person
        wb.contact_phone      = booking.contact_phone

        # Route
        wb.origin                   = booking.origin
        wb.origin_address           = booking.origin_address
        wb.destination              = booking.destination
        wb.destination_address      = booking.destination_address
        wb.expected_pickup_date     = self.expected_pickup_date
        wb.expected_delivery_date   = self.expected_delivery_date
        wb.distance_km              = booking.distance_km

        # Cargo
        wb.cargo_type           = booking.cargo_type
        wb.cargo_description    = booking.cargo_description
        wb.total_weight_kg      = booking.total_weight_kg
        wb.total_volume_cbm     = booking.total_volume_cbm
        wb.no_of_packages       = booking.no_of_packages
        wb.special_instructions = booking.special_instructions

        # Charges
        wb.service_type     = booking.service_type
        wb.rate_type        = booking.rate_type
        wb.base_rate        = booking.base_rate
        wb.currency         = booking.currency or "USD"
        wb.freight_charges  = booking.estimated_amount

        # Vehicles
        for row in vehicle_rows:
            wb.append("vehicles", {
                "vehicle":            row.vehicle,
                "vehicle_plate":      row.vehicle_plate,
                "vehicle_type":       row.vehicle_type,
                "driver":             row.driver,
                "driver_name":        row.driver_name,
                "driver_phone":       row.driver_phone,
                "assigned_weight_kg": row.assigned_weight_kg,
            })

        return wb
