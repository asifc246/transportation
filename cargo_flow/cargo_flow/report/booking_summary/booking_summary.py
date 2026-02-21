import frappe
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data    = get_data(filters)
    chart   = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"label": "Booking",          "fieldname": "name",             "fieldtype": "Link",     "options": "Booking",  "width": 140},
        {"label": "Date",             "fieldname": "booking_date",     "fieldtype": "Date",                            "width": 100},
        {"label": "Customer",         "fieldname": "customer",         "fieldtype": "Link",     "options": "Customer", "width": 160},
        {"label": "Type",             "fieldname": "booking_type",     "fieldtype": "Data",                            "width": 90},
        {"label": "Transport",        "fieldname": "transport_type",   "fieldtype": "Data",                            "width": 90},
        {"label": "Origin",           "fieldname": "origin",           "fieldtype": "Data",                            "width": 120},
        {"label": "Destination",      "fieldname": "destination",      "fieldtype": "Data",                            "width": 120},
        {"label": "Cargo Type",       "fieldname": "cargo_type",       "fieldtype": "Data",                            "width": 100},
        {"label": "Weight (KG)",      "fieldname": "total_weight_kg",  "fieldtype": "Float",                           "width": 100},
        {"label": "Est. Amount",      "fieldname": "estimated_amount", "fieldtype": "Currency",                        "width": 120},
        {"label": "Status",           "fieldname": "status",           "fieldtype": "Data",                            "width": 100},
        {"label": "Allocation",       "fieldname": "vehicle_allocation","fieldtype": "Link",    "options": "Vehicle Allocation", "width": 140},
        {"label": "Waybills",         "fieldname": "waybill_count",    "fieldtype": "Int",                             "width": 80},
    ]


def get_data(filters):
    conditions = get_conditions(filters)
    return frappe.db.sql(f"""
        SELECT
            name,
            booking_date,
            customer,
            booking_type,
            transport_type,
            origin,
            destination,
            cargo_type,
            total_weight_kg,
            estimated_amount,
            status,
            vehicle_allocation,
            waybill_count
        FROM `tabBooking`
        WHERE docstatus < 2
        {conditions}
        ORDER BY booking_date DESC, name DESC
    """, filters, as_dict=1)


def get_conditions(filters):
    conditions = ""
    if filters.get("from_date"):
        conditions += " AND booking_date >= %(from_date)s"
    if filters.get("to_date"):
        conditions += " AND booking_date <= %(to_date)s"
    if filters.get("customer"):
        conditions += " AND customer = %(customer)s"
    if filters.get("status"):
        conditions += " AND status = %(status)s"
    if filters.get("booking_type"):
        conditions += " AND booking_type = %(booking_type)s"
    return conditions


def get_chart(data):
    status_counts = {}
    for row in data:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1

    return {
        "data": {
            "labels": list(status_counts.keys()),
            "datasets": [{"values": list(status_counts.values())}],
        },
        "type": "donut",
        "title": "Bookings by Status",
        "colors": ["#5e64ff", "#2490ef", "#ff5858", "#36ba00", "#ffa00a", "#aaaaaa"],
    }


def get_summary(data):
    total      = len(data)
    confirmed  = sum(1 for r in data if r.status == "Confirmed")
    allocated  = sum(1 for r in data if r.status == "Allocated")
    in_transit = sum(1 for r in data if r.status == "In Transit")
    delivered  = sum(1 for r in data if r.status == "Delivered")
    total_amt  = sum(flt(r.estimated_amount) for r in data)

    return [
        {"label": "Total Bookings",  "value": total,      "indicator": "blue"},
        {"label": "Confirmed",       "value": confirmed,  "indicator": "blue"},
        {"label": "Allocated",       "value": allocated,  "indicator": "orange"},
        {"label": "In Transit",      "value": in_transit, "indicator": "yellow"},
        {"label": "Delivered",       "value": delivered,  "indicator": "green"},
        {"label": "Est. Revenue",    "value": total_amt,  "indicator": "green", "datatype": "Currency"},
    ]


def get_filters():
    return [
        {"fieldname": "from_date",    "label": "From Date",    "fieldtype": "Date",   "default": frappe.utils.add_months(frappe.utils.today(), -1)},
        {"fieldname": "to_date",      "label": "To Date",      "fieldtype": "Date",   "default": frappe.utils.today()},
        {"fieldname": "customer",     "label": "Customer",     "fieldtype": "Link",   "options": "Customer"},
        {"fieldname": "status",       "label": "Status",       "fieldtype": "Select", "options": "\nDraft\nConfirmed\nAllocated\nIn Transit\nDelivered\nCancelled"},
        {"fieldname": "booking_type", "label": "Booking Type", "fieldtype": "Select", "options": "\nImport\nExport\nDomestic"},
    ]
