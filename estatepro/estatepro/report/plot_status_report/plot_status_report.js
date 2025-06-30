// Copyright (c) 2025, Upeosoft Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Plot Status Report"] = {
	"filters": [

		{
			"fieldname": "project",
			"label": "Project",
			"fieldtype": "Link",
			"options": "Project",
			"reqd": 0
		},
		{
			"fieldname": "sale_status",
			"label": "Sale Status",
			"fieldtype": "Select",
			"options": "\nUnallocated\nBooked\nSold",
			"reqd": 0
		}

	]
};
