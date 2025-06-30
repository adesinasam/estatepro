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
        "Expenses:Currency:150"
    ]

def get_data(filters):
    conditions, params = get_conditions(filters)
    query = """
        SELECT
            DATE_FORMAT(pe.expense_date, %s) as month,
            SUM(pe.amount) as expenses
        FROM `tabProject Expense` pe
        WHERE pe.docstatus = 1
            AND pe.expense_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
            {conditions}
        GROUP BY DATE_FORMAT(pe.expense_date, %s)
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
                "name": "Expenses",
                "values": [row.expenses for row in data],
                "chartType": "line"
            }]
        },
        "type": "line",
        "colors": ["#39E4A5"]
    }

def get_conditions(filters):
    conditions = []
    params = []
    if filters.get("project"):
        conditions.append("pe.project = %s")
        params.append(filters.get("project"))
    return (" AND " + " AND ".join(conditions) if conditions else ""), params