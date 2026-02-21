frappe.query_reports["Booking Summary"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            reqd: 0,
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 0,
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
            options: "\nDraft\nConfirmed\nAllocated\nIn Transit\nDelivered\nCancelled",
        },
        {
            fieldname: "booking_type",
            label: __("Booking Type"),
            fieldtype: "Select",
            options: "\nImport\nExport\nDomestic",
        },
    ],
};
