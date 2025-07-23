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
        "Month:Data:150",
        "Plots Sold:Int:150"
    ]

def get_data(filters):
    conditions, params = get_conditions(filters)
    query = """
        SELECT
            DATE_FORMAT(ps.creation, %s) as month,
            COUNT(*) as plots_sold
        FROM `tabPlot Sales` ps
        WHERE ps.docstatus = 1
            AND ps.creation >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
            {conditions}
        GROUP BY DATE_FORMAT(ps.creation, %s)
        ORDER BY month
    """.format(conditions=conditions)
    data = frappe.db.sql(query, tuple(['%Y-%m', '%Y-%m'] + params), as_dict=True)
    return data

def get_chart_data(data):
    if not data:
        return None
    return {
        "data": {
            "labels": [row.month for row in data],
            "datasets": [{
                "name": "Plots Sold",
                "values": [row.plots_sold for row in data],
                "chartType": "line"
            }]
        },
        "type": "line",
        "colors": ["#449CF0"]
    }

def get_conditions(filters):
    conditions = []
    params = []
    if filters.get("project"):
        conditions.append("ps.project = %s")
        params.append(filters.get("project"))
    return (" AND " + " AND ".join(conditions) if conditions else ""), params