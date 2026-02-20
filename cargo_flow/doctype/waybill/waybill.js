frappe.ui.form.on("Waybill", {

    refresh(frm) {
        frm.trigger("render_status_badge");
        frm.trigger("setup_buttons");
        frm.trigger("calc_totals");
    },

    render_status_badge(frm) {
        const palette = {
            Draft:        "gray",
            Issued:       "blue",
            Dispatched:   "orange",
            "In Transit": "yellow",
            Delivered:    "green",
            Cancelled:    "red",
        };
        frm.page.set_indicator(frm.doc.status, palette[frm.doc.status] || "gray");
    },

    setup_buttons(frm) {
        if (frm.doc.docstatus !== 1) return;

        // ── Confirm Dispatch ─────────────────────────────────────
        if (frm.doc.status === "Issued") {
            frm.add_custom_button(__("Confirm Dispatch"), () => {
                frappe.confirm(
                    __("Confirm that cargo has been dispatched from <b>{0}</b>?", [frm.doc.origin]),
                    () => frappe.call({
                        method:   "confirm_dispatch",
                        doc:      frm.doc,
                        freeze:   true,
                        freeze_message: __("Updating…"),
                        callback() { frm.reload_doc(); },
                    })
                );
            }).addClass("btn-primary");
        }

        // ── Confirm Delivery ─────────────────────────────────────
        if (["Dispatched", "In Transit"].includes(frm.doc.status)) {
            frm.add_custom_button(__("Confirm Delivery"), () => {
                frm.trigger("open_delivery_dialog");
            }).addClass("btn-success");
        }

        // ── Quick nav ────────────────────────────────────────────
        if (frm.doc.booking) {
            frm.add_custom_button(__("Booking"), () => {
                frappe.set_route("Form", "Booking", frm.doc.booking);
            }, __("View"));
        }
        if (frm.doc.vehicle_allocation) {
            frm.add_custom_button(__("Vehicle Allocation"), () => {
                frappe.set_route("Form", "Vehicle Allocation", frm.doc.vehicle_allocation);
            }, __("View"));
        }
        if (frm.doc.invoice) {
            frm.add_custom_button(__("Invoice"), () => {
                frappe.set_route("Form", "Sales Invoice", frm.doc.invoice);
            }, __("View")).addClass("btn-success");
        }
    },

    open_delivery_dialog(frm) {
        const d = new frappe.ui.Dialog({
            title: __("Confirm Delivery"),
            fields: [
                {
                    fieldname:   "confirmed_by",
                    fieldtype:   "Data",
                    label:       __("Received By (Recipient Name)"),
                    reqd:        1,
                    description: __("Name of the person who received the cargo at {0}", [frm.doc.destination]),
                },
                {
                    fieldname: "remarks",
                    fieldtype: "Small Text",
                    label:     __("Delivery Remarks"),
                },
            ],
            primary_action_label: __("Confirm & Create Invoice"),
            primary_action(vals) {
                d.hide();
                frappe.call({
                    method:   "confirm_delivery",
                    doc:      frm.doc,
                    args:     { confirmed_by: vals.confirmed_by, remarks: vals.remarks },
                    freeze:   true,
                    freeze_message: __("Confirming delivery and creating invoice…"),
                    callback(r) {
                        if (r.message) {
                            frm.reload_doc();
                            frappe.show_alert({
                                message:   __("Invoice {0} created!", [r.message]),
                                indicator: "green",
                            }, 5);
                            setTimeout(() => {
                                frappe.set_route("Form", "Sales Invoice", r.message);
                            }, 1800);
                        }
                    },
                });
            },
        });
        d.show();
    },

    // ── Live charge totals ────────────────────────────────────────
    freight_charges(frm) { frm.trigger("calc_totals"); },

    calc_totals(frm) {
        let total = flt(frm.doc.freight_charges);
        (frm.doc.additional_charges || []).forEach(r => { total += flt(r.amount); });
        frm.set_value("total_charges", total);
    },
});

// Recalc when a charge row changes
frappe.ui.form.on("Waybill Charge", {
    amount(frm)              { frm.trigger("calc_totals"); },
    additional_charges_remove(frm) { frm.trigger("calc_totals"); },
});
