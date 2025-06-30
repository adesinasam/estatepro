import frappe

def execute(filters=None):
    filters = filters or {}

    columns = [
        {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 250},
        {"label": "Plots Sold", "fieldname": "sold", "fieldtype": "Int", "width": 150},
        {"label": "Plots Booked", "fieldname": "booked", "fieldtype": "Int", "width": 150},
        {"label": "Plots Available", "fieldname": "available", "fieldtype": "Int", "width": 150},
        {"label": "Total Plots", "fieldname": "total", "fieldtype": "Int", "width": 150}
    ]

    conditions = "1=1"
    if filters.get("project"):
        conditions += " AND pl.project = %(project)s"

    data = frappe.db.sql("""
        SELECT
            pl.project,
            SUM(CASE WHEN pl.status = 'Sold' THEN 1 ELSE 0 END) AS sold,
            SUM(CASE WHEN pl.status = 'Booked' THEN 1 ELSE 0 END) AS booked,
            SUM(CASE WHEN pl.status = 'Available' THEN 1 ELSE 0 END) AS available,
            COUNT(*) AS total
        FROM `tabPlot` pl
        LEFT JOIN `tabPlot Sale` ps ON ps.plot_name = pl.name AND ps.docstatus = 1
        WHERE {conditions}
        GROUP BY pl.project
    """.format(conditions=conditions), filters, as_dict=True)

    return columns, data
