# Cargo Flow

A Frappe/ERPNext app that implements a clean cargo management workflow:

```
Booking → Vehicle Allocation → Waybill → Sales Invoice (auto)
```

---

## Installation

### Requirements
- Frappe v14 or v15
- ERPNext (for Customer, Sales Invoice, Driver, Vehicle DocTypes)

### Install

```bash
# From your bench directory
bench get-app https://github.com/your-org/cargo_flow.git

# Install on your site
bench --site your-site.com install-app cargo_flow

# Run migrations
bench --site your-site.com migrate
```

---

## Workflow Overview

### 1. Booking (`CF-BK-YYYY-#####`)
Create a booking capturing:
- Customer & contact details
- Origin & destination with addresses
- Cargo details: type, weight (KG), volume (CBM), dimensions, packages
- Service type & rate (Fixed / Per KG / Per CBM / Per Package)
- Estimated amount is auto-calculated

**Submit** → status becomes `Confirmed`

Click **Create → Create Vehicle Allocation** to proceed.

---

### 2. Vehicle Allocation (`CF-VA-YYYY-#####`)
Auto-created from the Booking. Add one or more vehicles:
- Vehicle + plate number
- Driver + phone
- Assigned weight per vehicle

Choose waybill scope:
- **All Vehicles (Single Waybill)** — one waybill covers all vehicles
- **Each Vehicle (Separate Waybills)** — one waybill per vehicle

**Submit** → status becomes `Confirmed`

Click **Create → Create Waybill** to proceed.

---

### 3. Waybill (`CF-WB-YYYY-#####`)
Auto-populated from Booking + Allocation. Captures:
- Full route details
- Vehicle & driver list
- Freight charges + additional charges (fuel, handling, customs, etc.)
- Total charges (auto-summed)

**Submit** → status becomes `Issued`

Click **Confirm Dispatch** when cargo leaves → status: `Dispatched`

Click **Confirm Delivery** → enter recipient name → status: `Delivered`
→ **Sales Invoice is automatically created and submitted**

---

### 4. Sales Invoice
- Auto-created on delivery confirmation
- Line items: Freight Charges + each Additional Charge
- Linked back on the Waybill via the `Invoice` field
- View directly from Waybill → **View → Invoice**

---

## Roles

| Role | Access |
|---|---|
| `Cargo Booking Agent` | Create & submit Bookings; read Waybills |
| `Logistics Manager` | Manage Vehicle Allocations & Waybills |
| `Cargo Admin` | Full access to all DocTypes |

---

## Document Naming

| DocType | Format |
|---|---|
| Booking | `CF-BK-2024-00001` |
| Vehicle Allocation | `CF-VA-2024-00001` |
| Waybill | `CF-WB-2024-00001` |

---

## Status Flow

```
Booking:           Draft → Confirmed → Allocated → In Transit → Delivered
Vehicle Allocation: Draft → Confirmed → Dispatched → Delivered
Waybill:           Draft → Issued → Dispatched → Delivered
```

---

## Notes on ERPNext Integration

### Vehicle & Driver fields
`Vehicle Allocation Item` fetches from:
- `vehicle.license_plate` → plate number
- `vehicle.vehicle_type` → vehicle type
- `vehicle.payload` → capacity KG
- `driver.full_name` → driver name
- `driver.cell_number` → driver phone

If your Vehicle/Driver DocType uses different field names, update the `fetch_from` values in `vehicle_allocation_item.json`.

### Sales Invoice item_code
ERPNext Sales Invoice requires `item_code` if item validation is strict.
Options:
1. Create items named `"Freight Service"`, `"Fuel Surcharge"` etc. in ERPNext and map them in `waybill.py → _create_sales_invoice()`
2. Or disable item validation by adding `invoice.flags.ignore_mandatory = True` before `invoice.insert()` in `waybill.py`
