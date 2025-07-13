# Copyright (c) 2025, Adesina Akinyemi and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, add_months
from frappe.model.document import Document


class BulkPlotSale(Document):
    def validate(self):
        self.total_sale_amount = sum(row.sale_amount for row in self.plots)
        self.balance = self.total_sale_amount
        
        # Validate each plot in the child table
        for plot_row in self.plots:
            self.validate_plot_row(plot_row)

        if not self.company:
            self.company = frappe.defaults.get_user_default("Company")

    def validate_plot_row(self, plot_row):
        settings = frappe.get_single("EstatePro Accounts Settings")
        
        if settings.force_minimum_profit == 1:
            valuation = plot_row.valuation or 0
            min_profit_percent = settings.minimum_profit_percentage or 0
            min_sale_price = valuation + (valuation * min_profit_percent / 100)

            if plot_row.sale_amount < min_sale_price:
                frappe.throw(
                    f"Sale Amount for plot {plot_row.plot_name} must be greater than {min_profit_percent}% profit on valuation "
                    f"(Minimum acceptable: {min_sale_price:,.2f}) because 'Force Minimum Profit' is enabled in settings."
                )

    def before_save(self):
        self.set_default_accounts()

    def set_default_accounts(self):
        if not self.debit_to and self.customer:
            settings = frappe.get_single("EstatePro Accounts Settings")
            self.debit_to = settings.debtors_account
        if not self.against_income_account and self.customer:
            settings = frappe.get_single("EstatePro Accounts Settings")
            self.against_income_account = settings.unearned_revenue_account

    def on_submit(self):
        settings = frappe.get_single("EstatePro Accounts Settings")
        
        if not self.customer:
            frappe.throw("Customer is required to post to Debtors account.")
            
        if not self.plots:
            frappe.throw("At least one plot is required to submit Bulk Plot Sale.")

        created_sales = []
        for idx, plot_row in enumerate(self.plots):
            plot_sale = self.create_plot_sale(plot_row)
            plot_sale.submit()
            
            # Update the child table row with the created Plot Sale reference
            self.plots[idx].plot_sale = plot_sale.name
            created_sales.append(plot_sale.name)
            
        # Save the updated child table with plot_sale references
        self.save()
        
        frappe.msgprint(f"Created and submitted {len(created_sales)} Plot Sale documents")

    def create_plot_sale(self, plot_row):
        """Create individual Plot Sale document for each plot row"""
        plot_sale = frappe.new_doc("Plot Sale")
        
        # Copy fields from Bulk Plot Sale
        for field in ["company", "customer", "posting_date", "set_posting_time", "payment_status", 
        "customer_address", "address_display", "contact_person", "contact_display", "tc_name","terms", 
        "debit_to", "against_income_account", "campaign", "source", "customer_group", "remarks"]:
            plot_sale.set(field, self.get(field))
        
        # Set plot-specific fields
        plot_sale.plot_name = plot_row.plot_name
        plot_sale.plot = plot_row.plot
        plot_sale.project_creator = plot_row.project_creator
        plot_sale.plot_size = plot_row.plot_size
        plot_sale.project = plot_row.project
        plot_sale.cost_center = plot_row.cost_center
        plot_sale.valuation = plot_row.valuation
        plot_sale.sale_amount = plot_row.sale_amount
        plot_sale.allow_installment = plot_row.allow_installment
        plot_sale.payment_plan = plot_row.payment_plan
        plot_sale.down_payment_terms = plot_row.down_payment_terms
        plot_sale.set_downpayment_percentage = plot_row.set_downpayment_percentage
        plot_sale.down_payment_amount = plot_row.down_payment_amount
        plot_sale.down_payment_due_date = plot_row.down_payment_due_date
        plot_sale.installment_start_date = plot_row.installment_start_date
        
        # Set status
        plot_sale.status = "Submitted"
        
        # Link to the bulk sale
        # plot_sale.bulk_plot_sale = self.name
        
        # Save the document (will trigger validate)
        plot_sale.insert(ignore_permissions=True)
        
        return plot_sale

    def on_cancel(self):
        """Cancel all linked Plot Sales when bulk sale is cancelled"""
        for plot_row in self.plots:
            if plot_row.plot_sale:
                try:
                    plot_sale = frappe.get_doc("Plot Sale", plot_row.plot_sale)
                    if plot_sale.docstatus == 1:
                        plot_sale.cancel()
                    # frappe.db.set_value("Plot Sale", plot_row.plot_sale, "bulk_plot_sale", "")

                    plot_row.plot_sale = ""

                except frappe.DoesNotExistError:
                    pass
        
        # self.save()
        frappe.msgprint("All linked Plot Sale documents have been cancelled")
