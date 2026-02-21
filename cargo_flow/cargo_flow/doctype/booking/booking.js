frappe.ui.form.on("Booking", {

    refresh(frm) {
        frm.trigger("render_status_badge");
        frm.trigger("setup_buttons");
    },

    render_status_badge(frm) {
        const palette = {
            Draft:       "gray",
            Confirmed:   "blue",
            Allocated:   "orange",
            "In Transit":"yellow",
            Delivered:   "green",
            Cancelled:   "red",
        };
        frm.page.set_indicator(frm.doc.status, palette[frm.doc.status] || "gray");
    },

    setup_buttons(frm) {
        // ── Create Vehicle Allocation ───────────────────────────────
        if (frm.doc.docstatus === 1
            && frm.doc.status === "Confirmed"
            && !frm.doc.vehicle_allocation) {

            frm.add_custom_button(__("Create Vehicle Allocation"), () => {
                frappe.confirm(
                    __("Create a Vehicle Allocation for Booking <b>{0}</b>?", [frm.doc.name]),
                    () => frappe.call({
                        method: "create_vehicle_allocation",
                        doc:    frm.doc,
                        callback(r) {
                            if (r.message) {
                                frm.reload_doc();
                                frappe.set_route("Form", "Vehicle Allocation", r.message);
                            }
                        },
                    })
                );
            }, __("Create")).addClass("btn-primary");
        }

        // ── Quick-nav links ─────────────────────────────────────────
        if (frm.doc.vehicle_allocation) {
            frm.add_custom_button(__("Vehicle Allocation"), () => {
                frappe.set_route("Form", "Vehicle Allocation", frm.doc.vehicle_allocation);
            }, __("View"));
        }

        if (flt(frm.doc.waybill_count) > 0) {
            frm.add_custom_button(__("Waybills ({0})", [frm.doc.waybill_count]), () => {
                frappe.set_route("List", "Waybill", { booking: frm.doc.name });
            }, __("View"));
        }
    },

    // ── Live estimated amount ───────────────────────────────────────
    base_rate(frm)        { frm.trigger("calc_estimate"); },
    rate_type(frm)        { frm.trigger("calc_estimate"); },
    total_weight_kg(frm)  { frm.trigger("calc_estimate"); },
    total_volume_cbm(frm) { frm.trigger("calc_estimate"); },
    no_of_packages(frm)   { frm.trigger("calc_estimate"); },

    calc_estimate(frm) {
        const rate = flt(frm.doc.base_rate);
        if (!rate) { frm.set_value("estimated_amount", 0); return; }

        const qty_map = {
            "Fixed":       1,
            "Per KG":      flt(frm.doc.total_weight_kg),
            "Per CBM":     flt(frm.doc.total_volume_cbm),
            "Per Package": flt(frm.doc.no_of_packages),
        };
        frm.set_value("estimated_amount", rate * (qty_map[frm.doc.rate_type] || 0));
    },
});
