app_name = "cargo_flow"
app_title = "Cargo Flow"
app_publisher = "Your Company"
app_description = "Cargo management workflow: Booking → Vehicle Allocation → Waybill → Invoice"
app_email = "info@yourcompany.com"
app_license = "MIT"
app_version = "1.0.0"

# Required apps
required_apps = ["erpnext"]

# Document Events
doc_events = {}

# Fixtures - roles to auto-create on migrate
fixtures = [
    {
        "doctype": "Role",
        "filters": [
            ["role_name", "in", ["Cargo Booking Agent", "Logistics Manager", "Cargo Admin"]]
        ]
    }
]
