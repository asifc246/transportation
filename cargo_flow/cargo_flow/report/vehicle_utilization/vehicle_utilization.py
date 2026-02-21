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
        {"label": "Vehicle",           "fieldname": "vehicle",             "fieldtype": "Link",  "options": "Vehicle", "width": 140},
        {"label": "Plate No.",         "fieldname": "vehicle_plate",       "fieldtype": "Data",                        "width": 110},
        {"label": "Vehicle Type",      "fieldname": "vehicle_type",        "fieldtype": "Data",                        "width": 110},
        {"label": "Driver",            "fieldname": "driver",              "fieldtype": "Link",  "options": "Driver",  "width": 130},
        {"label": "Driver Name",       "fieldname": "driver_name",         "fieldtype": "Data",                        "width": 130},
        {"label": "Allocation",        "fieldname": "vehicle_allocation",  "fieldtype": "Link",  "options": "Vehicle Allocation", "width": 140},
        {"label": "Booking",           "fieldname": "booking",             "fieldtype": "Link",  "options": "Booking", "width": 140},
        {"label": "Customer",          "fieldname": "customer",            "fieldtype": "Data",                        "width": 150},
        {"label": "Origin",            "fieldname": "origin",              "fieldtype": "Data",                        "width": 120},
        {"label": "Destination",       "fieldname": "destination",         "fieldtype": "Data",                        "width": 120},
        {"label": "Pickup Date",       "fieldname": "expected_pickup_date","fieldtype": "Date",                        "width": 100},
        {"label": "Delivery Date",     "fieldname": "expected_delivery_date","fieldtype": "Date",                      "width": 110},
        {"label": "Assigned Wt (KG)",  "fieldname": "assigned_weight_kg",  "fieldtype": "Float",                       "width": 120},
        {"label": "Capacity (KG)",     "fieldname": "capacity_kg",         "fieldtype": "Float",                       "width": 110},
        {"label": "Utilization %",     "fieldname": "utilization_pct",     "fieldtype": "Percent",                     "width": 110},
        {"label": "Alloc. Status",     "fieldname": "status",              "fieldtype": "Data",                        "width": 110},
    ]


def get_data(filters):
    conditions = get_conditions(filters)

    rows = frappe.db.sql(f"""
        SELECT
            vai.vehicle,
            vai.vehicle_plate,
            vai.vehicle_type,
            vai.driver,
            vai.driver_name,
            vai.assigned_weight_kg,
            vai.capacity_kg,
            va.name  AS vehicle_allocation,
            va.booking,
            va.customer,
            va.origin,
            va.destination,
            va.expected_pickup_date,
            va.expected_delivery_date,
            va.status
        FROM `tabVehicle Allocation Item` vai
        INNER JOIN `tabVehicle Allocation` va ON va.name = vai.parent
        WHERE va.docstatus < 2
        {conditions}
        ORDER BY va.allocation_date DESC, vai.vehicle
    """, filters, as_dict=1)

    for row in rows:
        if flt(row.capacity_kg):
            row.utilization_pct = round(flt(row.assigned_weight_kg) / flt(row.capacity_kg) * 100, 1)
        else:
            row.utilization_pct = 0.0

    return rows


def get_conditions(filters):
    conditions = ""
    if filters.get("from_date"):
        conditions += " AND va.allocation_date >= %(from_date)s"
    if filters.get("to_date"):
        conditions += " AND va.allocation_date <= %(to_date)s"
    if filters.get("vehicle"):
        conditions += " AND vai.vehicle = %(vehicle)s"
    if filters.get("driver"):
        conditions += " AND vai.driver = %(driver)s"
    if filters.get("status"):
        conditions += " AND va.status = %(status)s"
    return conditions


def get_chart(data):
    # Group total assigned weight per vehicle
    vehicle_weight = {}
    for row in data:
        key = row.vehicle_plate or row.vehicle or "Unknown"
        vehicle_weight[key] = vehicle_weight.get(key, 0) + flt(row.assigned_weight_kg)

    # Top 10 vehicles by weight
    sorted_items = sorted(vehicle_weight.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "data": {
            "labels": [i[0] for i in sorted_items],
            "datasets": [{"name": "Assigned Weight (KG)", "values": [i[1] for i in sorted_items]}],
        },
        "type": "bar",
        "title": "Top Vehicles by Assigned Weight",
        "colors": ["#5e64ff"],
    }


def get_summary(data):
    total_trips     = len(data)
    unique_vehicles = len(set(r.vehicle for r in data if r.vehicle))
    unique_drivers  = len(set(r.driver for r in data if r.driver))
    total_weight    = sum(flt(r.assigned_weight_kg) for r in data)
    avg_util        = (
        sum(flt(r.utilization_pct) for r in data) / total_trips
        if total_trips else 0
    )

    return [
        {"label": "Total Trips",       "value": total_trips,                 "indicator": "blue"},
        {"label": "Unique Vehicles",   "value": unique_vehicles,             "indicator": "blue"},
        {"label": "Unique Drivers",    "value": unique_drivers,              "indicator": "blue"},
        {"label": "Total Weight (KG)", "value": round(total_weight, 2),      "indicator": "orange"},
        {"label": "Avg Utilization",   "value": f"{round(avg_util, 1)}%",    "indicator": "green"},
    ]
