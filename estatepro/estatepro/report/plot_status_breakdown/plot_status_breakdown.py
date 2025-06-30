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
        "Status:Data:150",
        "Count:Int:150"
    ]

def get_data(filters):
    conditions, params = get_conditions(filters)
    query = """
        SELECT
            pl.status as status,
            COUNT(*) as count
        FROM `tabPlot` pl
        WHERE 1=1 {conditions}
        GROUP BY pl.status
        ORDER BY pl.status
    """.format(conditions=conditions)
    data = frappe.db.sql(query, tuple(params), as_dict=True)
    return data

def get_chart_data(data):
    if not data:
        return None
    return {
        "data": {
            "labels": [row.status for row in data],
            "datasets": [{
                "values": [row.count for row in data]
            }]
        },
        "type": "donut",
        "colors": ["#39E4A5", "#ECAD4B", "#449CF0"]
    }

def get_conditions(filters):
    conditions = []
    params = []
    if filters.get("project"):
        conditions.append("pl.project = %s")
        params.append(filters.get("project"))
    return (" AND " + " AND ".join(conditions) if conditions else ""), params