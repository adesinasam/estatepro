
frappe.ui.form.on("EstatePro Accounts Settings", {
    setup: function(frm) {
        const account_fields = [
            'land_inventory_accont',
            'creditors_account',
            'expenses_included_in_valuation',
            'cost_of_goods_sold_account',
            'unearned_revenue_account',
            'sales_account',
            'debtors_account'
        ];
        
        account_fields.forEach(field => {
            frm.set_query(field, () => ({
                filters: {
                    company: frm.doc.default_company,
                    is_group: 0
                }
            }));
        });
    }
});