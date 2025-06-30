import frappe
from datetime import datetime, timedelta

def execute(filters=None):
    filters = filters or {}
    columns = get_columns(filters)
    data = get_data(filters)
    chart = get_chart_data(data)
    return columns, data, None, chart

def get_columns(filters):
    return [
        "Customer:Link/Customer:200",
        "Purchase Volume:Int:150"
    ]

def get_data(filters):
    conditions, params = get_conditions(filters)
    query = """
        SELECT
            ps.customer as customer,
            COUNT(ps.name) as purchase_volume
        FROM `tabPlot Sale` ps
        LEFT JOIN `tabPlot` pl ON ps.plot_name = pl.name
        WHERE ps.docstatus = 1 {conditions}
        GROUP BY ps.customer
        ORDER BY purchase_volume DESC
        LIMIT 5
    """.format(conditions=conditions)
    data = frappe.db.sql(query, tuple(params), as_dict=True)
    return data

def get_chart_data(data):
    if not data:
        return None
    return {
        "data": {
            "labels": [row.customer for row in data],
            "datasets": [{
                "name": "Purchase Volume",
                "values": [row.purchase_volume for row in data],
                "chartType": "bar"
            }]
        },
        "type": "bar",
        "colors": ["#449CF0"]
    }

def get_conditions(filters):
    conditions = []
    params = []
    if filters.get("project"):
        conditions.append("pl.project = %s")
        params.append(filters.get("project"))
    return (" AND " + " AND ".join(conditions) if conditions else ""), params