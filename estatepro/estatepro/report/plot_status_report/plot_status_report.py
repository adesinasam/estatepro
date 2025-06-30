# Copyright (c) 2025, Upeosoft Limited and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    
    return columns, data

def get_columns():
    return [
        {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 200},
        {"label": "Plot", "fieldname": "plot", "fieldtype": "Link", "options": "Plot", "width": 300},
        {"label": "Plot Size", "fieldname": "plot_size", "fieldtype": "Data", "width": 120},
        {"label": "Sale Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": "Valuation", "fieldname": "valuation", "fieldtype": "Currency", "width": 150},
    ]

def get_data(filters):
    conditions = " WHERE 1=1 "
    
    if filters.get("project"):
        conditions += f" AND p.project = '{filters.get('project')}'"
    
    if filters.get("status"):
        conditions += f" AND p.status = '{filters.get('status')}'"
    
    query = f"""
        SELECT
            p.project AS project,
            p.name AS plot,
            p.plot_size AS plot_size,
            p.status AS status,
            p.valuation AS valuation
        FROM `tabPlot` p
        {conditions}
        ORDER BY p.project, p.name
    """

    data = frappe.db.sql(query, as_dict=True)

    # Grouping logic by project
    grouped_data = []
    current_project = None

    for row in data:
        if row["project"] != current_project:
            grouped_data.append({
                "project": row["project"],
                "plot": f"== {row['project']} ==",
                "indent": 0
            })
            current_project = row["project"]

        row["indent"] = 1
        grouped_data.append(row)

    return grouped_data
