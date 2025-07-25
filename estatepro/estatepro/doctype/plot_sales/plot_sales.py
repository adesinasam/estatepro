# Copyright (c) 2025, Adesina Akinyemi and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, add_months
from frappe.model.document import Document
from frappe import _, msgprint, throw
from frappe.contacts.doctype.address.address import get_address_display


class PlotSales(Document):
    def validate(self):
        if frappe.flags.in_insert and frappe.db.exists("Plot Sales", self.name):
            frappe.throw("This Plot Sales record already exists.")

        self.balance = float(self.sale_amount) - float(self.total_paid or 0)
        self.project = frappe.db.get_value("Estate Project", self.estate_project, "project")

        # self.update_sales_team_from_customer()
        # self.calculate_incentives()

        if not self.company:
            self.company = frappe.defaults.get_user_default("Company")

        settings = frappe.get_single("EstatePro Accounts Settings")

        if settings.force_minimum_profit == 1:
            valuation = self.total_valuation or 0

            min_profit_percent = settings.minimum_profit_percentage or 0
            min_sale_price = valuation + (valuation * min_profit_percent / 100)

            if self.sale_amount < min_sale_price:
                frappe.throw(
                    f"Sale Amount must be greater than {min_profit_percent}% profit on valuation "
                    f"(Minimum acceptable: {min_sale_price:,.2f}) because 'Force Minimum Profit' is enabled in settings."
                )

    def before_save(self):
        self.set_payment_plan_from_project()

    def set_payment_plan_from_project(self):
        if not self.payment_plan and self.estate_project:
            if self.estate_project:
                project = frappe.get_doc('Estate Project', self.estate_project)
                if project.allow_installments == "Yes" and project.payment_period:
                    self.allow_installment = "Yes"
                    self.payment_period = project.payment_period

                    if project.down_payment_terms == "Amount":
                        self.down_payment = project.down_payment_amount or 0
                    else:  # Assume Percent
                        self.down_payment = self.sale_amount * (project.set_downpayment_percentage or 0) / 100
        if not self.debit_to and self.customer:
            settings = frappe.get_single("EstatePro Accounts Settings")
            self.debit_to = settings.debtors_account
        if not self.against_income_account and self.customer:
            settings = frappe.get_single("EstatePro Accounts Settings")
            self.against_income_account = settings.unearned_revenue_account


    def on_submit(self):
        settings = frappe.get_single("EstatePro Accounts Settings")

        debtors_account = self.debit_to
        unearned_revenue_account = settings.unearned_revenue_account
        self.balance = float(self.sale_amount) - float(self.total_paid or 0)

        if not self.customer:
            frappe.throw("Customer is required to post to Debtors account.")

        if not self.project:
            frappe.throw("Project is required to post journal entry.")

        # Create initial Journal Entry (Debtors vs Unearned Revenue)
        je = frappe.new_doc("Journal Entry")
        je.posting_date = self.posting_date
        je.company = self.company or frappe.defaults.get_user_default("Company")
        je.voucher_type = "Journal Entry"
        je.remark = f"Initial Plot Sales record of Project {self.estate_project} for Customer {self.customer}"
        je.project = self.project
        je.title = self.name

        je.append("accounts", {
            "account": debtors_account,
            "party_type": "Customer",
            "party": self.customer,
            "debit_in_account_currency": self.sale_amount,
            "project": self.project,
            "cost_center": self.cost_center            
        })

        je.append("accounts", {
            "account": unearned_revenue_account,
            "credit_in_account_currency": self.sale_amount,
            "project": self.project,
            "cost_center": self.cost_center            
        })

        je.save()
        je.submit()
        self.db_set("sales_journal_entry", je.name)

        # Update land bin
        for plot_row in self.plots:
            land_bin_name = plot_row.land_bin

            if not land_bin_name:
                frappe.throw(f"No Land Bin found for project {self.estate_project} and plot size {plot_row.plot_size}")

            # Get the Land Bin document
            land_bin = frappe.get_doc("Land Bin", land_bin_name)

            # Update quantities
            ordered_qty = (land_bin.ordered_qty or 0) + (plot_row.qty or 0)
            actual_qty = (land_bin.actual_qty or 0) - (plot_row.qty or 0)
            stock_value = land_bin.valuation_rate * actual_qty

            # Using db.set_value
            frappe.db.set_value("Land Bin", land_bin_name, {
                "ordered_qty": ordered_qty,
                "actual_qty": actual_qty,
                "stock_value": stock_value
            })

        # Generate payment schedule
        project = frappe.get_doc("Estate Project", self.estate_project)
        allow_installments = project.allow_installments

        if allow_installments == "Yes":
            if project.down_payment_terms == "Amount":
                down = round(project.down_payment_amount or 0, 2)
            else:  # Assume Percent
                down_pct = float(project.set_downpayment_percentage or 0)
                down = round(self.sale_amount * down_pct / 100, 2)

            balance = round(self.sale_amount - down, 2)
            months = self.payment_plan if self.payment_plan else 0

            sched = frappe.new_doc("Plot Payment Schedule")
            sched.plot_sale = self.name
            sched.sale_date = self.posting_date

            def add_row(ptype, ddate, amt):
                sched.append("plot_payment", {
                    "payment_type": ptype,
                    "due_date": ddate,
                    "amount": amt,
                    "paid_amount": 0.0,
                    "status": "Unpaid"
                })

            # Use user-entered Down Payment Due Date
            add_row("Downpayment", self.down_payment_due_date or nowdate(), down)

            if allow_installments and months:
                per = round(balance / months, 2)
                total_install = per * months
                adjustment = round(balance - total_install, 2)
                start = self.installment_start_date or nowdate()
                for i in range(months):
                    amt = per + (adjustment if i == months - 1 else 0)
                    due_date = add_months(start, i)
                    add_row("Installment", due_date, amt)

            sched.save()
            frappe.msgprint(f"Payment schedule created: {sched.name}")

    def update_sales_team_from_customer(self):
        if not self.customer:
            self.sales_team = []
            return
        
        customer = frappe.get_doc("Customer", self.customer)
        if not customer.sales_team:
            return
        
        self.set("sales_team", [])
        for row in customer.sales_team:
            self.append("sales_team", {
                "sales_person": row.sales_person,
                "allocated_percentage": row.allocated_percentage,
                "commission_rate": row.commission_rate,
                "incentives": (row.allocated_percentage / 100) * self.sale_amount if self.sale_amount else 0
            })
    
    def calculate_incentives(self):
        if not self.sale_amount or not self.sales_team:
            return
        
        for row in self.sales_team:
            row.incentives = (row.allocated_percentage / 100) * self.sale_amount

    def on_cancel(self):
        # Cancel and delete linked Journal Entry
        if self.sales_journal_entry:
            je = frappe.get_doc("Journal Entry", self.sales_journal_entry)
            if je.docstatus == 1:
                je.cancel()
            self.db_set("sales_journal_entry", "")

        # Update land bin quantities
        for plot_row in self.plots:
            land_bin_name = plot_row.land_bin

            if land_bin_name:
                land_bin = frappe.get_doc("Land Bin", land_bin_name)
                ordered_qty = (land_bin.ordered_qty or 0) - (plot_row.qty or 0)
                actual_qty = (land_bin.actual_qty or 0) + (plot_row.qty or 0)
                stock_value = land_bin.valuation_rate * actual_qty

            frappe.db.set_value("Land Bin", land_bin_name, {
                    "ordered_qty": ordered_qty,
                    "actual_qty": actual_qty,
                    "stock_value": stock_value
                }, ignore_permissions=True)

        # Delete payment schedule if exists
        payment_schedule = frappe.db.get_value("Plot Payment Schedule", {"plot_sale": self.name})
        if payment_schedule:
            frappe.delete_doc("Plot Payment Schedule", payment_schedule)

        frappe.msgprint(f"Plot Sales {self.name} has been cancelled successfully")

@frappe.whitelist()
def get_payment_schedule(plot_sale):
    rows = frappe.get_all("Plot Payment Schedule", filters={"plot_sale": plot_sale}, fields=["name"])
    return rows and rows[0].name or None
