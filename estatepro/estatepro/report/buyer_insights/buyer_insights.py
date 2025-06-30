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
        "Total:Data:150",
        "Partially Paid:Int:150",
        "Fully Paid:Int:150",
        "Unpaid:Int:150",
        "Defaulted:Int:150"
    ]

def get_data(filters):
    conditions, params = get_conditions(filters)
    query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN ps.payment_status = 'Partly Paid' THEN 1 ELSE 0 END) as partially_paid,
            SUM(CASE WHEN ps.payment_status = 'Paid' THEN 1 ELSE 0 END) as fully_paid,
            SUM(CASE WHEN ps.payment_status = 'Pending' THEN 1 ELSE 0 END) as unpaid,
            SUM(CASE WHEN ps.payment_status = 'Defaulted' THEN 1 ELSE 0 END) as defaulted
        FROM `tabPlot` pl
        LEFT JOIN `tabPlot Sale` ps ON ps.plot_name = pl.name AND ps.docstatus = 1
        WHERE 1=1 {conditions}
    """.format(conditions=conditions)
    data = frappe.db.sql(query, tuple(params), as_dict=True)
    return data

def get_chart_data(data):
    if not data:
        return None
    row = data[0]
    return {
        "data": {
            "labels": ["Fully Paid", "Unpaid", "Partially Paid", "Defaulted"],
            "datasets": [{
                "values": [
                    row.get("fully_paid", 0),
                    row.get("unpaid", 0),
                    row.get("partially_paid", 0),
                    row.get("defaulted", 0)
                ],
                "colors": ["#449CF0", "#ECAD4B", "#CB2929", "#39E4A5"]
            }]
        },
        "type": "pie"
    }

def get_conditions(filters):
    conditions = []
    params = []
    if filters.get("project"):
        conditions.append("pl.project = %s")
        params.append(filters.get("project"))
    return (" AND " + " AND ".join(conditions) if conditions else ""), params