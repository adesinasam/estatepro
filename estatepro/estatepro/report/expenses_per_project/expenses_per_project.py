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
        "Expenses:Currency:150"
    ]

def get_data(filters):
    conditions, params = get_conditions(filters)
    query = """
        SELECT
            pe.project as project,
            SUM(pe.amount) as expenses
        FROM `tabProject Expense` pe
        WHERE pe.docstatus = 1 {conditions}
        GROUP BY pe.project
        ORDER BY expenses DESC
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
                "name": "Expenses",
                "values": [row.expenses for row in data],
                "chartType": "bar"
            }]
        },
        "type": "bar",
        "colors": ["#ECAD4B"]
    }

def get_conditions(filters):
    conditions = []
    params = []
    if filters.get("project"):
        conditions.append("pe.project = %s")
        params.append(filters.get("project"))
    if filters.get("period") == "MTD":
        conditions.append("MONTH(pe.expense_date) = MONTH(CURDATE()) AND YEAR(pe.expense_date) = YEAR(CURDATE())")
    elif filters.get("period") == "YTD":
        conditions.append("YEAR(pe.expense_date) = YEAR(CURDATE())")
    return (" AND " + " AND ".join(conditions) if conditions else ""), params