# Copyright (c) 2025, Upeosoft Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Plot(Document):
	pass






@frappe.whitelist()
def sell_plot(plot_name):
	# Fetch the plot document
	plot = frappe.get_doc("Plot", plot_name)

	# Perform your logic here (e.g., mark it as sold, create a Sales Invoice, etc.)
	if plot.status == "Sold":
		frappe.throw(_("This plot is already sold."))

	plot.status = "Sold"
	plot.save()
	frappe.msgprint(_("Plot {0} has been marked as sold.".format(plot_name)))
