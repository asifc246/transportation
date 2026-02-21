import frappe
from frappe.utils import flt, time_diff_in_hours


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data    = get_data(filters)
    chart   = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"label": "Waybill",           "fieldname": "name",                    "fieldtype": "Link",     "options": "Waybill",   "width": 140},
        {"label": "Date",              "fieldname": "waybill_date",             "fieldtype": "Date",                             "width": 100},
        {"label": "Booking",           "fieldname": "booking",                  "fieldtype": "Link",     "options": "Booking",   "width": 140},
        {"label": "Customer",          "fieldname": "customer",                 "fieldtype": "Link",     "options": "Customer",  "width": 150},
        {"label": "Origin",            "fieldname": "origin",                   "fieldtype": "Data",                             "width": 120},
        {"label": "Destination",       "fieldname": "destination",              "fieldtype": "Data",                             "width": 120},
        {"label": "Cargo Type",        "fieldname": "cargo_type",               "fieldtype": "Data",                             "width": 100},
        {"label": "Weight (KG)",       "fieldname": "total_weight_kg",          "fieldtype": "Float",                            "width": 100},
        {"label": "Exp. Pickup",       "fieldname": "expected_pickup_date",     "fieldtype": "Date",                             "width": 100},
        {"label": "Exp. Delivery",     "fieldname": "expected_delivery_date",   "fieldtype": "Date",                             "width": 110},
        {"label": "Actual Pickup",     "fieldname": "actual_pickup_datetime",   "fieldtype": "Datetime",                         "width": 140},
        {"label": "Actual Delivery",   "fieldname": "actual_delivery_datetime", "fieldtype": "Datetime",                         "width": 140},
        {"label": "Transit Hrs",       "fieldname": "transit_hours",            "fieldtype": "Float",                            "width": 100},
        {"label": "Status",            "fieldname": "status",                   "fieldtype": "Data",                             "width": 100},
        {"label": "Received By",       "fieldname": "delivery_confirmed_by",    "fieldtype": "Data",                             "width": 130},
        {"label": "Total Charges",     "fieldname": "total_charges",            "fieldtype": "Currency",                         "width": 120},
        {"label": "Invoice",           "fieldname": "invoice",                  "fieldtype": "Link",     "options": "Sales Invoice", "width": 140},
    ]


def get_data(filters):
    conditions = get_conditions(filters)

    rows = frappe.db.sql(f"""
        SELECT
            name,
            waybill_date,
            booking,
            customer,
            origin,
            destination,
            cargo_type,
            total_weight_kg,
            expected_pickup_date,
            expected_delivery_date,
            actual_pickup_datetime,
            actual_delivery_datetime,
            status,
            delivery_confirmed_by,
            total_charges,
            invoice
        FROM `tabWaybill`
        WHERE docstatus < 2
        {conditions}
        ORDER BY waybill_date DESC, name DESC
    """, filters, as_dict=1)

    for row in rows:
        if row.actual_pickup_datetime and row.actual_delivery_datetime:
            row.transit_hours = round(
                time_diff_in_hours(row.actual_delivery_datetime, row.actual_pickup_datetime), 2
            )
        else:
            row.transit_hours = None

    return rows


def get_conditions(filters):
    conditions = ""
    if filters.get("from_date"):
        conditions += " AND waybill_date >= %(from_date)s"
    if filters.get("to_date"):
        conditions += " AND waybill_date <= %(to_date)s"
    if filters.get("customer"):
        conditions += " AND customer = %(customer)s"
    if filters.get("status"):
        conditions += " AND status = %(status)s"
    if filters.get("booking"):
        conditions += " AND booking = %(booking)s"
    return conditions


def get_chart(data):
    status_counts = {}
    for row in data:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1

    color_map = {
        "Draft":      "#aaaaaa",
        "Issued":     "#5e64ff",
        "Dispatched": "#ffa00a",
        "In Transit": "#ffdd00",
        "Delivered":  "#36ba00",
        "Cancelled":  "#ff5858",
    }
    labels = list(status_counts.keys())

    return {
        "data": {
            "labels": labels,
            "datasets": [{"values": list(status_counts.values())}],
        },
        "type": "donut",
        "title": "Waybills by Status",
        "colors": [color_map.get(l, "#5e64ff") for l in labels],
    }


def get_summary(data):
    total     = len(data)
    issued    = sum(1 for r in data if r.status == "Issued")
    dispatched = sum(1 for r in data if r.status == "Dispatched")
    delivered = sum(1 for r in data if r.status == "Delivered")
    invoiced  = sum(1 for r in data if r.invoice)

    delivered_rows  = [r for r in data if r.transit_hours]
    avg_transit     = (
        sum(r.transit_hours for r in delivered_rows) / len(delivered_rows)
        if delivered_rows else 0
    )

    return [
        {"label": "Total Waybills",   "value": total,                         "indicator": "blue"},
        {"label": "Issued",           "value": issued,                        "indicator": "blue"},
        {"label": "Dispatched",       "value": dispatched,                    "indicator": "orange"},
        {"label": "Delivered",        "value": delivered,                     "indicator": "green"},
        {"label": "Invoiced",         "value": invoiced,                      "indicator": "green"},
        {"label": "Avg Transit (Hrs)","value": round(avg_transit, 1),         "indicator": "blue"},
    ]
