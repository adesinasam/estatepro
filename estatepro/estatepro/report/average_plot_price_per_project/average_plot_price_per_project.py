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
        "Project:Link/Project:200",
        "Average Price:Currency:150"
    ]

def get_data(filters):
    conditions, params = get_conditions(filters)
    query = """
        SELECT
            ps.project as project,
            AVG(ps.sale_amount) as average_price
        FROM `tabPlot Sale` ps
        WHERE ps.docstatus = 1 {conditions}
        GROUP BY ps.project
        ORDER BY average_price DESC
    """.format(conditions=conditions)
    data = frappe.db.sql(query, tuple(params), as_dict=True)
    return data

def get_chart_data(data):
    if not data:
        return None
    return {
        "data": {
            "labels": [row.project for row in data],
            "datasets": [{
                "name": "Average Price",
                "values": [row.average_price for row in data],
                "chartType": "bar"
            }]
        },
        "type": "bar",
        "colors": ["#CB2929"]
    }

def get_conditions(filters):
    conditions = []
    params = []
    if filters.get("project"):
        conditions.append("ps.project = %s")
        params.append(filters.get("project"))
    return (" AND " + " AND ".join(conditions) if conditions else ""), params