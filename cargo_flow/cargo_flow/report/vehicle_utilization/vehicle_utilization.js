frappe.query_reports["Vehicle Utilization"] = {
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
            fieldname: "vehicle",
            label: __("Vehicle"),
            fieldtype: "Link",
            options: "Vehicle",
        },
        {
            fieldname: "driver",
            label: __("Driver"),
            fieldtype: "Link",
            options: "Driver",
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nDraft\nConfirmed\nDispatched\nIn Transit\nDelivered\nCancelled",
        },
    ],
};
