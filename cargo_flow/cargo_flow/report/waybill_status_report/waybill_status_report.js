frappe.query_reports["Waybill Status Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
        {
            fieldname: "customer",
            label: __("Customer"),
            fieldtype: "Link",
            options: "Customer",
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nDraft\nIssued\nDispatched\nIn Transit\nDelivered\nCancelled",
        },
        {
            fieldname: "booking",
            label: __("Booking"),
            fieldtype: "Link",
            options: "Booking",
        },
    ],
};
