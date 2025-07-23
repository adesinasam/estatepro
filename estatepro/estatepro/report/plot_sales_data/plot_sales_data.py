import frappe
from datetime import datetime, timedelta

def execute(filters=None):
    filters = filters or {}
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        "Project:Link/Project:250",
        "Plots Sold:Int:150",
        "Plots Booked:Int:150",
        "Plots Available:Int:150",
        "Total Plots:Int:150",
        "Total Collected:Currency:150",
        "Outstanding Payments:Currency:150",
        "Payment Status:Select:150"
    ]

def get_data(filters):
    conditions, params = get_conditions(filters)
    query = """
        SELECT
            pl.project as project,
            SUM(CASE WHEN pl.status = 'Sold' THEN 1 ELSE 0 END) as plots_sold,
            SUM(CASE WHEN pl.status = 'Booked' THEN 1 ELSE 0 END) as plots_booked,
            SUM(CASE WHEN pl.status = 'Available' THEN 1 ELSE 0 END) as plots_available,
            COUNT(*) as total,
            COALESCE(SUM(CASE WHEN ps.docstatus = 1 THEN ps.total_paid ELSE 0 END), 0) as total_collected,
            COALESCE(SUM(CASE WHEN ps.docstatus = 1 THEN ps.balance ELSE 0 END), 0) as outstanding_payments,
            COALESCE(GROUP_CONCAT(DISTINCT ps.payment_status), 'None') as payment_status
        FROM `tabPlot` pl
        LEFT JOIN `tabPlot Sales` ps ON ps.plot_name = pl.name AND ps.docstatus = 1
        WHERE 1=1 {conditions}
        GROUP BY pl.project
    """.format(conditions=conditions)
    data = frappe.db.sql(query, tuple(params), as_dict=True)
    return data

def get_conditions(filters):
    conditions = []
    params = []
    if filters.get("project"):
        conditions.append("pl.project = %s")
        params.append(filters.get("project"))
    return (" AND " + " AND ".join(conditions) if conditions else ""), params