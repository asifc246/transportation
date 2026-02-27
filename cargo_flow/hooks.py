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
    },
    {
        "doctype": "Custom Field",
        "filters": [
            ["name", "in", 
             [
                "Driver-custom_type",
                "Driver-custom_iqama_expiry_date",
                "Driver-custom_iqama_issuing_date",
                "Driver-custom_iqama_number",
                "Vehicle-custom_is_rented",
                "Vehicle-custom_trip_type",
                "Vehicle-custom_driver",
                "Vehicle-custom_driver_included",
                "Vehicle-custom_maintenance_included",
                "Vehicle-custom_fuel_included",
                "Vehicle-custom_type_details",
                "Vehicle-custom_type",
                "Vehicle-custom_column_break_m2dkh",
                "Vehicle-custom_rental",
                "Vehicle-custom_provider"
            ]]
        ]
    }
]
