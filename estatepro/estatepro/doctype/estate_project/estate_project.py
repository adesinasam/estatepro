# Copyright (c) 2025, Adesina Akinyemi and contributors
# For license information, please see license.txt

import frappe
import math
from frappe.model.document import Document


class EstateProject(Document):
    def validate(self):
        # Ensure purchase_price is considered, defaulting to 0 if None
        total_cost = self.purchase_price or 0
        
        # Sum all amount_spent values in the value_addition child table
        if self.get("value_addition"):
            total_cost += sum(item.amount_spent or 0 for item in self.value_addition)

        # Assign the computed total cost to total_project_cost
        self.total_project_cost = total_cost

        # Compute Gross Sale Value from plots_details table
        gross_sale_value = 0
        if self.get("plots_details"):
            gross_sale_value = sum((plot.number_of_plots or 0) * (plot.valuation or 0) for plot in self.plots_details)

        # Assign the computed Gross Sale Value
        self.gross_sale_value = gross_sale_value

        # Compute the difference amount
        self.difference_amount = gross_sale_value - total_cost

        # Compute the balance
        self.balance = (self.total_project_cost or 0) - (self.total_paid or 0)

    
    def before_submit(self):
        if not self.value_addition and not self.has_no_value_addition:
            frappe.throw("You cannot submit this document without adding records to the Value Addition Detail table or checking 'Has No Value Addition'.")

        if not self.plots_details:
            frappe.throw("You cannot submit this document without adding records to the Plots Details table.")
            
           # Allow tolerance for very small floating point differences
        if not math.isclose(self.difference_amount, 0.0, abs_tol=0.01):
            if not (self.ignore_difference_amount and -1.0 <= self.difference_amount < 1.0):

                frappe.throw("The Difference Amount MUST be 0. Ensure that you have spread the plots costs well to match the total land cost. If the difference is very small( between -1 and 1), you can check 'Ignore Difference Amount'.")

        # if self.difference_amount != 0:

        #     frappe.throw("The Difference Amount MUST be 0. Ensure that you have spread the plots costs well to match the total land cost.")


    def on_submit(self):
        try:
            project = self.create_project() 
            self.create_plots(project_name=project.name, project=self.name, creator_name=self.project_name)
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Project Creation Error")
            frappe.throw(f"An error occurred while creating the project: {str(e)}")



    def create_project(self):
        """Creates a new Project and links it to this Estate Project"""
        try:
            if self.project:
                project = frappe.get_doc('Project', self.project)
                project.db_set('status', 'Open')
                project.db_set('project_name', self.project_name)
            else:
                # Create the ERPNext Project document
                project = frappe.new_doc("Project")
                project.project_name = self.project_name
                project.custom_project_creator_id = self.name  # track origin
                project.insert()

                # Link the created project to the Estate Project's 'project' field
                self.project = project.name
                self.db_set("project", project.name)  # ensures it's saved even if in on_submit

            frappe.db.commit()
            frappe.msgprint(f"Project '{project.name}' created and linked successfully.")

            return project

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Project Creation Failed")
            frappe.throw(f"Failed to create project: {str(e)}")

            frappe.throw(f"Failed to create project: {str(e)}")


    def create_plots(self, project_name, project, creator_name):
        """Generates plots as Items in Item Master"""
        plot_details = self.get("plots_details")

        if not plot_details:
            frappe.throw("No plot details provided.")

        try:
            total_plots = sum([d.number_of_plots for d in plot_details])
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Error Processing Plot Details")
            frappe.throw("Error calculating total plots.")

        # Fetch existing plot numbers and determine the next available number
        existing_ids = frappe.get_all("Plot", fields=["plot_number"])
        used_numbers = set()
        for r in existing_ids:
            num_str = r.plot_number.replace("PLT", "")
            if num_str.isdigit():
                used_numbers.add(int(num_str))

        next_number = 1
        def get_next_unique_id():
            nonlocal next_number
            while next_number in used_numbers:
                next_number += 1
            used_numbers.add(next_number)
            return str(next_number).zfill(5)

        for detail in plot_details:
            try:
                plot_size = detail.plot_size
                count = detail.number_of_plots  
                valuation = detail.valuation 
                plot_prefix = detail.plot_prefix
                count_number = 0

                for _ in range(count):
                    count_number += 1
                    plot_id = get_next_unique_id()
                    plot_name = f"{creator_name} - {plot_size} - {plot_prefix} {count_number}" 

                    plot = frappe.new_doc("Plot")
                    plot.project = project
                    plot.plot_name = plot_name
                    plot.plot_number = plot_id
                    plot.plot_size = plot_size  
                    plot.plot_size_link = plot_size  
                    plot.valuation = valuation

                    plot.insert()
                    frappe.db.commit()

                # Create landbin for each plot size
                landbin = frappe.new_doc("Land Bin")
                landbin.plot_size = plot_size  
                landbin.estate_project = project
                landbin.actual_qty = count
                landbin.projected_qty = count
                landbin.project = self.project
                landbin.valuation_rate = float(valuation)
                landbin.stock_value = float(count * valuation)

                landbin.insert()
                frappe.db.commit()

            except Exception as e:
                frappe.log_error(frappe.get_traceback(), f"Failed to create plot {plot_id}")
                frappe.msgprint(f"Skipping plot {plot_id} due to an error: {str(e)}", alert=True)

        frappe.msgprint(f"{total_plots} plots created successfully for project {project_name}.")


    def get_number_format(self, total_plots):
        """Determine correct zero-padding based on total plots."""
        if total_plots < 10:
            return 2
        elif total_plots < 100:
            return 3
        else:
            return 4
        

    def before_cancel(self):
        non_available_plots = frappe.get_all(
            "Plot",
            filters={
                "project": self.name,
                "status": ["!=", "Available"]
            },
            pluck="name"
        )

        if non_available_plots:
            message = "You cannot cancel this project because the following plots are already in sales pipeline:\n" + \
                    ", ".join(non_available_plots)
            frappe.throw(message)


    def on_cancel(self):
        # Delete linked Project
        project = frappe.get_doc('Project', self.project)
        try:
            project.db_set('status', 'Cancelled')
            frappe.db.commit()
        except Exception as e:
            frappe.throw(f"Cannot delete Estate Project because the linked Project '{project.name}' could not be updated. Error: {str(e)}")

        # Delete related Plots
        plot_names = frappe.get_all(
            "Plot",
            filters={"project": self.name},
            pluck="name"
        )
        for plot_name in plot_names:
            try:
                frappe.delete_doc("Plot", plot_name, ignore_permissions=True, force=True)
            except Exception as e:
                frappe.log_error(f"Failed to delete Plot {plot_name}", str(e))

        # Delete related Land Bin
        bin_names = frappe.get_all(
            "Land Bin",
            filters={"estate_project": self.name},
            pluck="name"
        )
        for bin_name in bin_names:
            try:
                frappe.delete_doc("Land Bin", bin_name, ignore_permissions=True, force=True)
            except Exception as e:
                frappe.log_error(f"Failed to delete Land Bin {bin_name}", str(e))
