// Copyright (c) 2026, Company and contributors
// For license information, please see license.txt

frappe.ui.form.on('Absence Exemption', {
	onload: function(frm) {
		if (frm.is_new() && !frm.doc.start_date) {
			frm.set_value('start_date', frappe.datetime.get_today());
			frm.set_value('end_date', frappe.datetime.get_today());
		}
	},
	validate: function(frm) {
		if (frm.doc.start_date && frm.doc.end_date) {
			if (frm.doc.end_date < frm.doc.start_date) {
				frappe.msgprint(__('结束日期不能早于开始日期'));
				frappe.validated = false;
			}
		}
	}
});
