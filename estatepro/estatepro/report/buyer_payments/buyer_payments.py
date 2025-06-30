import frappe
from datetime import datetime, timedelta

def execute(filters=None):
    filters = filters or {}
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    return [
        "Customer:Link/Customer:200",
        "Amount Paid:Currency:150",
        "Amount Remaining:Currency:150",
        "Plot Bought:Link/Plot:200"
    ]

def get_data(filters):
    conditions, params = get_conditions(filters)
    query = """
        SELECT
            ps.customer as customer,
            ps.total_paid as amount_paid,
            ps.balance as amount_remaining,
            ps.plot_name as plot_bought
        FROM `tabPlot Sale` ps
        LEFT JOIN `tabPlot` pl ON ps.plot_name = pl.name
        WHERE ps.docstatus = 1 {conditions}
        ORDER BY ps.customer
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