// Copyright (c) 2026, Company and contributors
// For license information, please see license.txt

frappe.listview_settings['Project Member'] = {
	add_fields: ['email', 'mobile', 'user_id', 'is_manager', 'is_active'],
	onload: function(listview) {
		listview.page.add_inner_button(__('从飞书通讯录同步成员'), function() {
			frappe.confirm(__('是否立即从飞书通讯录拉取并同步团队成员列表？'), function() {
				frappe.call({
					method: 'dev_workbench.api.v1.members.import_feishu_contacts',
					freeze: true,
					freeze_message: __('正在从飞书通讯录同步成员...'),
					callback: function(r) {
						if (r.message && r.message.status === 'success') {
							frappe.msgprint({
								title: __('同步成功'),
								message: r.message.message,
								indicator: 'green'
							});
							listview.refresh();
						}
					}
				});
			});
		});
	}
};
