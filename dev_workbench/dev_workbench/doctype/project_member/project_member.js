// Copyright (c) 2026, Company and contributors
// For license information, please see license.txt

frappe.ui.form.on('Project Member', {
	refresh: function(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__('认领未归属 Git 身份'), function() {
				frappe.call({
					method: 'dev_workbench.api.v1.members.get_unclaimed_identities',
					callback: function(r) {
						let unclaimed = (r.message || []).map(item => ({
							label: `${item.identity} (${item.identity_type})`,
							value: item.name
						}));

						if (unclaimed.length === 0) {
							frappe.msgprint(__('当前暂无可认领的 Git 身份。所有提交身份均已归属。'));
							return;
						}

						let d = new frappe.ui.Dialog({
							title: __('认领 Git 身份到成员: ') + frm.doc.member_name,
							fields: [
								{
									label: __('选择待认领身份'),
									fieldname: 'identity_name',
									fieldtype: 'Select',
									options: unclaimed,
									reqd: 1
								}
							],
							primary_action_label: __('确认认领'),
							primary_action: function(values) {
								frappe.call({
									method: 'dev_workbench.api.v1.members.claim_git_identity',
									args: {
										member_id: frm.doc.name,
										identity_name: values.identity_name
									},
									callback: function(res) {
										if (res.message && res.message.status === 'success') {
											frappe.show_alert({
												message: res.message.message,
												indicator: 'green'
											});
											d.hide();
											frm.reload_doc();
										}
									}
								});
							}
						});
						d.show();
					}
				});
			}, __('Git 身份'));

			frm.add_custom_button(__('添加新 Git 身份'), function() {
				frappe.prompt([
					{
						label: __('身份标识 (邮箱或用户名)'),
						fieldname: 'identity',
						fieldtype: 'Data',
						reqd: 1
					},
					{
						label: __('身份类型'),
						fieldname: 'identity_type',
						fieldtype: 'Select',
						options: 'Email\nUsername',
						default: 'Email'
					}
				], function(values) {
					frappe.call({
						method: 'dev_workbench.api.v1.members.add_git_identity',
						args: {
							member_id: frm.doc.name,
							identity: values.identity,
							identity_type: values.identity_type
						},
						callback: function(res) {
							if (res.message && res.message.status === 'success') {
								frappe.show_alert({
									message: res.message.message,
									indicator: 'green'
								});
								frm.reload_doc();
							}
						}
					});
				}, __('为成员添加 Git 身份'));
			}, __('Git 身份'));
		}
	}
});
