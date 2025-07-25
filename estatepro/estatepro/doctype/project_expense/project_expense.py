# Copyright (c) 2025, Adesina Akinyemi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.meta import get_field_precision
from frappe.utils import cint, flt
from frappe.utils import nowdate


class ProjectExpense(Document):
    def validate(self):
        if not self.paying_account and self.amount > 0:
            frappe.throw(
                f"Paying Account cannot be empty since Paid Amount is greater than zero"
            )

        self.validate_line_plots()
        self.set_total_expense()
        self.set_applicable_charges_on_item()

    def validate_line_plots(self):
        for d in self.get("plots", []):
            if d.estate_project_plot and not frappe.db.exists(
                "Plot Details",
                {"name": d.estate_project_plot, "parent": d.estate_project},
            ):
                frappe.throw(
                    _("Row {0}: Plot {1} does not exist in Estate Project {2}").format(
                        d.idx,
                        frappe.bold(d.estate_project_plot),
                        frappe.bold(d.estate_project),
                    )
                )
 
    def set_total_expense(self):
        self.total_expense = sum(flt(d.amount_spent) for d in self.get("expenses"))

    def set_applicable_charges_on_item(self):
        if self.get("expenses") and self.distribute_charges_based_on != "Distribute Manually":
            total_item_cost = 0.0
            total_charges = 0.0
            item_count = 0
            based_on_field = frappe.scrub(self.distribute_charges_based_on)

            for item in self.get("plots"):
                total_item_cost += item.get(based_on_field)

            for item in self.get("plots"):
                if not total_item_cost and not item.get(based_on_field):
                    frappe.throw(
                        _(
                            "It's not possible to distribute charges equally when total amount is zero, please set 'Distribute Charges Based On' as 'Quantity'"
                        )
                    )

                item.applicable_charges = flt(
                    flt(item.get(based_on_field))
                    * (flt(self.total_expense) / flt(total_item_cost)),
                    item.precision("applicable_charges"),
                )
                total_charges += item.applicable_charges
                item_count += 1

            if total_charges != self.total_expense:
                diff = self.total_expense - total_charges
                self.get("plots")[item_count - 1].applicable_charges += diff

    def validate_applicable_charges_for_item(self):
        if self.distribute_charges_based_on == "Distribute Manually" and len(self.expenses) > 1:
            frappe.throw(
                _(
                    "Please keep one Applicable Charges, when 'Distribute Charges Based On' is 'Distribute Manually'. For more charges, please create another Landed Cost Voucher."
                )
            )

        based_on = self.distribute_charges_based_on.lower()

        if based_on != "distribute manually":
            total = sum(flt(d.get(based_on)) for d in self.get("plots"))
        else:
            # consider for proportion while distributing manually
            total = sum(flt(d.get("applicable_charges")) for d in self.get("plots"))

        if not total:
            frappe.throw(
                _(
                    "Total {0} for all Plots is zero, may be you should change 'Distribute Charges Based On'"
                ).format(based_on)
            )

        total_applicable_charges = sum(flt(d.applicable_charges) for d in self.get("plots"))

        precision = get_field_precision(
            frappe.get_meta("Expense Estate Project Details").get_field("applicable_charges"),
            currency=frappe.get_cached_value("Company", self.company, "default_currency"),
        )

        diff = flt(self.total_expense) - flt(total_applicable_charges)
        diff = flt(diff, precision)

        if abs(diff) < (2.0 / (10**precision)):
            self.plots[-1].applicable_charges += diff
        else:
            frappe.throw(
                _(
                    "Total Applicable Charges in Plot Details table must be same as Total Expenses and Charges"
                )
            )

    def on_submit(self):
        try:
            self.validate_applicable_charges_for_item()
            self.update_landed_cost()
            self.create_journal_entry()
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(frappe.get_traceback(), "Project Expense: Journal Entry Error")
            frappe.throw(f"An error occurred while creating the journal entry: {str(e)}")

    def update_landed_cost(self):
        for plot_row in self.plots:
            # Update land bin
            # First find the Land Bin name
            land_bin_name = frappe.db.get_value(
                "Land Bin",
                filters={
                    'estate_project': self.estate_project, 
                    'plot_size': plot_row.plot_size
                },
                fieldname='name'
            )

            if not land_bin_name:
                frappe.throw(f"No Land Bin found for project {self.estate_project} and plot size {plot_row.plot_size}")

            # Get the Land Bin document
            land_bin = frappe.get_doc("Land Bin", land_bin_name)

            # Update quantities
            actual_qty = flt(land_bin.actual_qty)
            stock_value = flt(land_bin.stock_value) + flt(plot_row.applicable_charges)
            valuation_rate = stock_value / actual_qty if actual_qty else 0

            # Using db.set_value
            frappe.db.set_value("Land Bin", land_bin_name, {
                "valuation_rate": valuation_rate,
                "stock_value": stock_value
            })

            # Delete related Plots
            plot_names = frappe.get_all(
                "Plot",
                filters={
                "project": self.estate_project,
                "plot_size_link": plot_row.plot_size
                },
                pluck="name"
            )
            for plot_name in plot_names:
                try:
                    frappe.db.set_value("Plot", plot_name, {
                        "valuation": valuation_rate
                    })
                except Exception as e:
                    frappe.log_error(f"Failed to Update Plot {plot_name}", str(e))


    def create_journal_entry(self):
        try:
            settings = frappe.get_single("EstatePro Accounts Settings")

            creditors_account=settings.creditors_account
            land_inventory_accont = settings.land_inventory_accont

            # Get the paying account from the Project Expense document
            if self.amount > 0:
                paying_account = self.paying_account
                if not paying_account:
                    frappe.throw("Paying account is not set.")

            if self.is_paid:
                for expense_row in self.expenses:
                    expense_account = expense_row.expense_account
                    amount_spent = expense_row.amount_spent

                    if not expense_account:
                        frappe.throw(f"No Expense Account found for Value Addition Item {expense_row.value_addition_item}")

                 #Create a Journal Entry
                 journal_entry = frappe.new_doc("Journal Entry")
                 journal_entry.voucher_type = "Journal Entry"
                 je.company = self.company
                 journal_entry.posting_date = self.expense_date
                 journal_entry.user_remark = f"Valuation addition expense for Estate Project {self.estate_project}"

                 # 1 Create Debit entry (Land Stock)
                 journal_entry.append("accounts", {
                     "account": land_inventory_accont,
                     "debit_in_account_currency": self.total_expense,
                     "credit_in_account_currency": 0,
                     "project": self.project,
                     "cost_center": self.cost_center
                 })

                 # 2 Create Credit entry (Paying Account)
                 journal_entry.append("accounts", {
                     "account": paying_account,
                     "credit_in_account_currency": self.total_expense,
                     "debit_in_account_currency": 0,
                     "project": self.project,
                     "cost_center": self.cost_center
                 })

                    # Submit the Journal Entry
                    journal_entry.insert(ignore_permissions=True)
                    journal_entry.submit()

            else:
                # Create a Journal Entry
                journal_entry = frappe.new_doc("Journal Entry")
                journal_entry.voucher_type = "Journal Entry"
                je.company = self.company
                journal_entry.posting_date = self.expense_date
                journal_entry.user_remark = f"Valuation addition expense for Estate Project {self.estate_project}"

                # 1 Create Debit entry (Land Stock)
                journal_entry.append("accounts", {
                    "account": land_inventory_accont,
                    "debit_in_account_currency": self.total_expense,
                    "credit_in_account_currency": 0,
                    "project": self.project,
                    "cost_center": self.cost_center
                })

                # 2 Create Credit entry (Creditor Account)
                journal_entry.append("accounts", {
                    "account": creditors_account,
                    "party_type": "Supplier",
                    "party": self.supplier,
                    "credit_in_account_currency": self.total_expense,
                    "debit_in_account_currency": 0,
                    "project": self.project,
                    "cost_center": self.cost_center
                })

                if self.amount > 0:
                    # 3 Create Debit entry (Creditor Account)
                    journal_entry.append("accounts", {
                        "account": creditors_account,
                        "party_type": "Supplier",
                        "party": self.supplier,
                        "debit_in_account_currency": self.amount,
                        "credit_in_account_currency": 0,
                        "project": self.project,
                        "cost_center": self.cost_center
                    })

                    # 4 Create Credit entry (Paying Account)
                    journal_entry.append("accounts", {
                        "account": paying_account,
                        "credit_in_account_currency": self.amount,
                        "debit_in_account_currency": 0,
                        "project": self.project,
                        "cost_center": self.cost_center
                    })

                # Submit the Journal Entry
                journal_entry.insert(ignore_permissions=True)
                journal_entry.submit()

            self.db_set("journal_entry", journal_entry.name)
            frappe.msgprint(f"Project Expense created successfully.")
        except frappe.DoesNotExistError as e:
            frappe.throw(f"A required document does not exist: {str(e)}")
        except frappe.ValidationError as e:
            frappe.throw(f"Validation error: {str(e)}")
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Project Expense: Journal Entry Error")
            frappe.throw(f"An unexpected error occurred: {str(e)}")

    @frappe.whitelist()
    def get_plot_size_details(self):
        self.set("plots", [])
        if self.estate_project:
            plot_details = get_plot_details(self.estate_project)

            for d in plot_details:
                    plot = self.append("plots")
                    plot.plot_size = d.plot_size
                    plot.qty = d.number_of_plots
                    plot.rate = d.valuation
                    plot.amount = d.number_of_plots * d.valuation
                    plot.estate_project = self.estate_project
                    plot.estate_project_plot = d.name


def get_plot_details(estate_project):
    plot = frappe.qb.DocType("Plot Size")
    plot_detail = frappe.qb.DocType("Plot Details")
    return (
        frappe.qb.from_(plot_detail)
        .inner_join(plot)
        .on(plot.name == plot_detail.plot_size)
        .select(
            plot_detail.plot_size,
            plot_detail.number_of_plots,
            plot_detail.valuation,
            plot_detail.total_valuation,
            plot_detail.parent,
            plot_detail.name,
        )
        .where(
            (plot_detail.parent == estate_project)
        )
        .run(as_dict=True)
    )
