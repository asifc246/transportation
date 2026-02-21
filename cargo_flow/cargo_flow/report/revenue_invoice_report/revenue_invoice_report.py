import frappe
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data    = get_data(filters)
    chart   = get_chart(data, filters)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {"label": "Waybill",         "fieldname": "waybill",          "fieldtype": "Link",     "options": "Waybill",       "width": 140},
        {"label": "Delivery Date",   "fieldname": "delivery_date",    "fieldtype": "Date",                                  "width": 110},
        {"label": "Customer",        "fieldname": "customer",         "fieldtype": "Link",     "options": "Customer",       "width": 160},
        {"label": "Booking",         "fieldname": "booking",          "fieldtype": "Link",     "options": "Booking",        "width": 140},
        {"label": "Route",           "fieldname": "route",            "fieldtype": "Data",                                  "width": 180},
        {"label": "Cargo Type",      "fieldname": "cargo_type",       "fieldtype": "Data",                                  "width": 100},
        {"label": "Service Type",    "fieldname": "service_type",     "fieldtype": "Data",                                  "width": 120},
        {"label": "Freight Charges", "fieldname": "freight_charges",  "fieldtype": "Currency",                              "width": 130},
        {"label": "Extra Charges",   "fieldname": "extra_charges",    "fieldtype": "Currency",                              "width": 120},
        {"label": "Total Charges",   "fieldname": "total_charges",    "fieldtype": "Currency",                              "width": 120},
        {"label": "Currency",        "fieldname": "currency",         "fieldtype": "Data",                                  "width": 80},
        {"label": "Invoice",         "fieldname": "invoice",          "fieldtype": "Link",     "options": "Sales Invoice",  "width": 140},
        {"label": "Invoice Status",  "fieldname": "invoice_status",   "fieldtype": "Data",                                  "width": 110},
        {"label": "Outstanding",     "fieldname": "outstanding_amount","fieldtype": "Currency",                             "width": 120},
    ]


def get_data(filters):
    conditions = get_conditions(filters)

    rows = frappe.db.sql(f"""
        SELECT
            w.name              AS waybill,
            w.actual_delivery_datetime AS delivery_date,
            w.customer,
            w.booking,
            CONCAT(w.origin, ' → ', w.destination) AS route,
            w.cargo_type,
            w.service_type,
            w.freight_charges,
            (w.total_charges - w.freight_charges) AS extra_charges,
            w.total_charges,
            w.currency,
            w.invoice
        FROM `tabWaybill` w
        WHERE w.docstatus = 1
          AND w.status = 'Delivered'
        {conditions}
        ORDER BY w.actual_delivery_datetime DESC
    """, filters, as_dict=1)

    # Enrich with invoice status and outstanding amount
    for row in rows:
        if row.invoice:
            inv = frappe.db.get_value(
                "Sales Invoice",
                row.invoice,
                ["status", "outstanding_amount"],
                as_dict=1,
            )
            if inv:
                row.invoice_status    = inv.status
                row.outstanding_amount = flt(inv.outstanding_amount)
        else:
            row.invoice_status     = "Not Created"
            row.outstanding_amount = flt(row.total_charges)

    return rows


def get_conditions(filters):
    conditions = ""
    if filters.get("from_date"):
        conditions += " AND DATE(w.actual_delivery_datetime) >= %(from_date)s"
    if filters.get("to_date"):
        conditions += " AND DATE(w.actual_delivery_datetime) <= %(to_date)s"
    if filters.get("customer"):
        conditions += " AND w.customer = %(customer)s"
    if filters.get("invoice_status"):
        if filters["invoice_status"] == "Not Invoiced":
            conditions += " AND (w.invoice IS NULL OR w.invoice = '')"
        else:
            conditions += " AND w.invoice IS NOT NULL AND w.invoice != ''"
    return conditions


def get_chart(data, filters):
    # Monthly revenue grouped by delivery month
    monthly = {}
    for row in data:
        if row.delivery_date:
            month = str(row.delivery_date)[:7]   # YYYY-MM
            monthly[month] = monthly.get(month, 0) + flt(row.total_charges)

    sorted_months = sorted(monthly.items())

    return {
        "data": {
            "labels": [m[0] for m in sorted_months],
            "datasets": [{"name": "Revenue", "values": [m[1] for m in sorted_months]}],
        },
        "type": "bar",
        "title": "Monthly Revenue",
        "colors": ["#36ba00"],
        "axisOptions": {"xIsSeries": 1},
    }


def get_summary(data):
    total_revenue    = sum(flt(r.total_charges) for r in data)
    total_freight    = sum(flt(r.freight_charges) for r in data)
    total_extra      = sum(flt(r.extra_charges) for r in data)
    total_outstanding = sum(flt(r.outstanding_amount) for r in data)
    invoiced_count   = sum(1 for r in data if r.invoice)
    not_invoiced     = sum(1 for r in data if not r.invoice)

    return [
        {"label": "Total Revenue",     "value": total_revenue,     "indicator": "green",  "datatype": "Currency"},
        {"label": "Freight Revenue",   "value": total_freight,     "indicator": "green",  "datatype": "Currency"},
        {"label": "Extra Charges",     "value": total_extra,       "indicator": "blue",   "datatype": "Currency"},
        {"label": "Outstanding",       "value": total_outstanding, "indicator": "orange", "datatype": "Currency"},
        {"label": "Invoiced",          "value": invoiced_count,    "indicator": "green"},
        {"label": "Not Invoiced",      "value": not_invoiced,      "indicator": "red"},
    ]
