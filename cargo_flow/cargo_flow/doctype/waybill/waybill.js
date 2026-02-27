// frappe.ui.form.on("Waybill", {

//     refresh(frm) {
//         frm.trigger("render_status_badge");
//         frm.trigger("setup_buttons");
//         frm.trigger("calc_totals");
//     },

//     render_status_badge(frm) {
//         const palette = {
//             Draft:        "gray",
//             Issued:       "blue",
//             Dispatched:   "orange",
//             "In Transit": "yellow",
//             Delivered:    "green",
//             Cancelled:    "red",
//         };
//         frm.page.set_indicator(frm.doc.status, palette[frm.doc.status] || "gray");
//     },

//     setup_buttons(frm) {
//         if (frm.doc.docstatus !== 1) return;

//         // ── Confirm Dispatch ─────────────────────────────────────
//         if (frm.doc.status === "Issued") {
//             frm.add_custom_button(__("Confirm Dispatch"), () => {
//                 frappe.confirm(
//                     __("Confirm that cargo has been dispatched from <b>{0}</b>?", [frm.doc.origin]),
//                     () => frappe.call({
//                         method:   "confirm_dispatch",
//                         doc:      frm.doc,
//                         freeze:   true,
//                         freeze_message: __("Updating…"),
//                         callback() { frm.reload_doc(); },
//                     })
//                 );
//             }).addClass("btn-primary");
//         }

//         // ── Confirm Delivery ─────────────────────────────────────
//         if (["Dispatched", "In Transit"].includes(frm.doc.status)) {
//             frm.add_custom_button(__("Confirm Delivery"), () => {
//                 frm.trigger("open_delivery_dialog");
//             }).addClass("btn-success");
//         }

//         // ── Quick nav ────────────────────────────────────────────
//         if (frm.doc.booking) {
//             frm.add_custom_button(__("Booking"), () => {
//                 frappe.set_route("Form", "Booking", frm.doc.booking);
//             }, __("View"));
//         }
//         if (frm.doc.vehicle_allocation) {
//             frm.add_custom_button(__("Vehicle Allocation"), () => {
//                 frappe.set_route("Form", "Vehicle Allocation", frm.doc.vehicle_allocation);
//             }, __("View"));
//         }
//         if (frm.doc.invoice) {
//             frm.add_custom_button(__("Invoice"), () => {
//                 frappe.set_route("Form", "Sales Invoice", frm.doc.invoice);
//             }, __("View")).addClass("btn-success");
//         }
//     },

//     open_delivery_dialog(frm) {
//         const d = new frappe.ui.Dialog({
//             title: __("Confirm Delivery"),
//             fields: [
//                 {
//                     fieldname:   "confirmed_by",
//                     fieldtype:   "Data",
//                     label:       __("Received By (Recipient Name)"),
//                     reqd:        1,
//                     description: __("Name of the person who received the cargo at {0}", [frm.doc.destination]),
//                 },
//                 {
//                     fieldname: "remarks",
//                     fieldtype: "Small Text",
//                     label:     __("Delivery Remarks"),
//                 },
//             ],
//             primary_action_label: __("Confirm & Create Invoice"),
//             primary_action(vals) {
//                 d.hide();
//                 frappe.call({
//                     method:   "confirm_delivery",
//                     doc:      frm.doc,
//                     args:     { confirmed_by: vals.confirmed_by, remarks: vals.remarks },
//                     freeze:   true,
//                     freeze_message: __("Confirming delivery and creating invoice…"),
//                     callback(r) {
//                         if (r.message) {
//                             frm.reload_doc();
//                             frappe.show_alert({
//                                 message:   __("Invoice {0} created!", [r.message]),
//                                 indicator: "green",
//                             }, 5);
//                             setTimeout(() => {
//                                 frappe.set_route("Form", "Sales Invoice", r.message);
//                             }, 1800);
//                         }
//                     },
//                 });
//             },
//         });
//         d.show();
//     },

//     // ── Live charge totals ────────────────────────────────────────
//     freight_charges(frm) { frm.trigger("calc_totals"); },

//     calc_totals(frm) {
//         let total = flt(frm.doc.freight_charges);
//         (frm.doc.additional_charges || []).forEach(r => { total += flt(r.amount); });
//         frm.set_value("total_charges", total);
//     },
// });

// // Recalc when a charge row changes
// frappe.ui.form.on("Waybill Charge", {
//     amount(frm)              { frm.trigger("calc_totals"); },
//     additional_charges_remove(frm) { frm.trigger("calc_totals"); },
// });


frappe.ui.form.on("Waybill", {

    setup(frm) {
        frm.set_query("vehicle", "expenses", function(doc, cdt, cdn) {
            // collect vehicles from child table `vehicles`
            let vehicle_list = (doc.vehicles || [])
                .map(row => row.vehicle)
                .filter(v => v);

            return {
                filters: [
                    ["Vehicle", "name", "in", vehicle_list.length ? vehicle_list : [""]]
                ]
            };
        });
    },

    refresh(frm) {
        frm.trigger("render_status_badge");
        frm.trigger("setup_buttons");
        frm.trigger("calc_totals");
    },

    render_status_badge(frm) {
        const palette = {
            Draft: "gray", Issued: "blue", Dispatched: "orange",
            "In Transit": "yellow", Delivered: "green", Cancelled: "red",
        };
        frm.page.set_indicator(frm.doc.status, palette[frm.doc.status] || "gray");
    },

    setup_buttons(frm) {
        if (frm.doc.docstatus !== 1) return;

        // ── Confirm Dispatch ─────────────────────────────────────
        if (frm.doc.status === "Issued") {
            frm.add_custom_button(__("Confirm Dispatch"), () => {
                frappe.confirm(
                    __("Confirm dispatch from <b>{0}</b>?", [frm.doc.origin]),
                    () => frappe.call({
                        method: "confirm_dispatch", doc: frm.doc,
                        freeze: true, freeze_message: __("Updating…"),
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

        // ── Generate Purchase Invoice ─────────────────────────────
        if (frm.doc.status === "Delivered" && !frm.doc.purchase_invoice) {
            frm.add_custom_button(__("Generate Purchase Invoice"), () => {
                frm.trigger("open_purchase_invoice_dialog");
            }, __("Create"));
        }

        // ── Navigation links ──────────────────────────────────────
        if (frm.doc.booking)
            frm.add_custom_button(__("Booking"), () =>
                frappe.set_route("Form", "Booking", frm.doc.booking), __("View"));

        if (frm.doc.vehicle_allocation)
            frm.add_custom_button(__("Vehicle Allocation"), () =>
                frappe.set_route("Form", "Vehicle Allocation", frm.doc.vehicle_allocation), __("View"));

        if (frm.doc.invoice)
            frm.add_custom_button(__("Sales Invoice"), () =>
                frappe.set_route("Form", "Sales Invoice", frm.doc.invoice), __("View"));

        if (frm.doc.purchase_invoice)
            frm.add_custom_button(__("Purchase Invoice"), () =>
                frappe.set_route("Form", "Purchase Invoice", frm.doc.purchase_invoice), __("View"));
    },

    // ── Delivery confirmation dialog ──────────────────────────────
    open_delivery_dialog(frm) {
        const d = new frappe.ui.Dialog({
            title: __("Confirm Delivery"),
            fields: [
                {
                    fieldname: "confirmed_by", fieldtype: "Data",
                    label: __("Received By (Recipient Name)"), reqd: 1,
                },
                {
                    fieldname: "remarks", fieldtype: "Small Text",
                    label: __("Delivery Remarks"),
                },
            ],
            primary_action_label: __("Confirm & Create Sales Invoice"),
            primary_action(vals) {
                d.hide();
                frappe.call({
                    method: "confirm_delivery", doc: frm.doc,
                    args: { confirmed_by: vals.confirmed_by, remarks: vals.remarks },
                    freeze: true, freeze_message: __("Confirming delivery…"),
                    callback(r) {
                        if (r.message) {
                            frm.reload_doc();
                            frappe.show_alert({ message: __("Sales Invoice {0} created!", [r.message]), indicator: "green" }, 5);
                            setTimeout(() => frappe.set_route("Form", "Sales Invoice", r.message), 1800);
                        }
                    },
                });
            },
        });
        d.show();
    },

    // ── Purchase Invoice dialog ───────────────────────────────────
    open_purchase_invoice_dialog(frm) {
        // Collect unique suppliers from expense rows
        const suppliers = [...new Set(
            (frm.doc.expenses || []).map(r => r.supplier).filter(Boolean)
        )];
        const default_supplier = suppliers[0] || "";

        const d = new frappe.ui.Dialog({
            title: __("Generate Purchase Invoice"),
            fields: [
                {
                    fieldname: "info", fieldtype: "HTML",
                    options: `<p class="text-muted small">
                        One Purchase Invoice will be created for all expense rows on this Waybill.
                        The supplier defaults to the most common supplier in your expense rows,
                        or the vehicle's rental provider. You can override it below.
                    </p>`,
                },
                {
                    fieldname: "supplier", fieldtype: "Link",
                    label: __("Supplier"), options: "Supplier",
                    default: default_supplier, reqd: 1,
                    description: __("Default from expense rows / rental provider. Override if needed."),
                },
            ],
            primary_action_label: __("Create Purchase Invoice"),
            primary_action(vals) {
                d.hide();
                frappe.call({
                    method: "generate_purchase_invoice", doc: frm.doc,
                    args: { supplier: vals.supplier },
                    freeze: true, freeze_message: __("Creating Purchase Invoice…"),
                    callback(r) {
                        if (r.message) {
                            frm.reload_doc();
                            frappe.show_alert({ message: __("Purchase Invoice {0} created!", [r.message]), indicator: "green" }, 5);
                            setTimeout(() => frappe.set_route("Form", "Purchase Invoice", r.message), 1800);
                        }
                    },
                });
            },
        });
        d.show();
    },

    // ── Charge totals ─────────────────────────────────────────────
    freight_charges(frm) { frm.trigger("calc_totals"); },

    calc_totals(frm) {
        let charges = flt(frm.doc.freight_charges);
        (frm.doc.additional_charges || []).forEach(r => { charges += flt(r.amount); });
        frm.set_value("total_charges", charges);

        let expenses = 0;
        (frm.doc.expenses || []).forEach(r => { expenses += flt(r.amount); });
        frm.set_value("total_expenses", expenses);
    },
});

// ── Additional Charges child ──────────────────────────────────────
frappe.ui.form.on("Waybill Charge", {
    amount(frm) { frm.trigger("calc_totals"); },
    additional_charges_remove(frm) { frm.trigger("calc_totals"); },
});

// ── Expense child — auto-fill supplier from vehicle rental provider ─
frappe.ui.form.on("Waybill Expense", {
    vehicle(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.vehicle) return;
        frappe.db.get_value("Vehicle", row.vehicle, "custom_provider", (data) => {
            if (data && data.custom_provider && !row.supplier) {
                frappe.model.set_value(cdt, cdn, "supplier", data.custom_provider);
            }
        });
    },
    amount(frm) { frm.trigger("calc_totals"); },
    expenses_remove(frm) { frm.trigger("calc_totals"); },
});
