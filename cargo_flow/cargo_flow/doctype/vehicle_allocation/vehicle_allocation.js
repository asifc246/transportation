frappe.ui.form.on("Vehicle Allocation", {

    refresh(frm) {
        frm.trigger("render_status_badge");
        frm.trigger("setup_buttons");
    },

    render_status_badge(frm) {
        const palette = {
            Draft:        "gray",
            Confirmed:    "blue",
            Dispatched:   "orange",
            "In Transit": "yellow",
            Delivered:    "green",
            Cancelled:    "red",
        };
        frm.page.set_indicator(frm.doc.status, palette[frm.doc.status] || "gray");
    },

    setup_buttons(frm) {
        // ── Create Waybill ──────────────────────────────────────────
        if (frm.doc.docstatus === 1 && frm.doc.status !== "Cancelled") {
            frm.add_custom_button(__("Create Waybill"), () => {
                frm.trigger("open_waybill_dialog");
            }, __("Create")).addClass("btn-primary");
        }

        // ── Quick nav ───────────────────────────────────────────────
        if (frm.doc.booking) {
            frm.add_custom_button(__("Booking"), () => {
                frappe.set_route("Form", "Booking", frm.doc.booking);
            }, __("View"));
        }

        if (flt(frm.doc.waybill_count) > 0) {
            frm.add_custom_button(__("Waybills ({0})", [frm.doc.waybill_count]), () => {
                frappe.set_route("List", "Waybill", { vehicle_allocation: frm.doc.name });
            }, __("View"));
        }
    },

    open_waybill_dialog(frm) {
        const d = new frappe.ui.Dialog({
            title: __("Create Waybill"),
            fields: [
                {
                    fieldname:   "waybill_scope",
                    fieldtype:   "Select",
                    label:       __("Create Waybill For"),
                    options:     ["All Vehicles (Single Waybill)", "Each Vehicle (Separate Waybills)"],
                    default:     frm.doc.waybill_scope || "All Vehicles (Single Waybill)",
                    description: __("Single waybill covers all vehicles. Separate creates one per vehicle."),
                    reqd:        1,
                },
            ],
            primary_action_label: __("Create"),
            primary_action(vals) {
                // Save scope selection first, then call server
                frm.set_value("waybill_scope", vals.waybill_scope);
                frm.save().then(() => {
                    frappe.call({
                        method:   "create_waybill",
                        doc:      frm.doc,
                        freeze:   true,
                        freeze_message: __("Creating Waybill(s)…"),
                        callback(r) {
                            if (r.message && r.message.length) {
                                d.hide();
                                frm.reload_doc();
                                if (r.message.length === 1) {
                                    frappe.set_route("Form", "Waybill", r.message[0]);
                                } else {
                                    frappe.set_route("List", "Waybill", {
                                        vehicle_allocation: frm.doc.name,
                                    });
                                }
                            }
                        },
                    });
                });
            },
        });
        d.show();
    },
});
