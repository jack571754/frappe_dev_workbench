# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import frappe

from dev_workbench.permissions import MANAGER_ROLE


def ensure_manager_role():
	"""Create the application role once; DocType JSON owns its permissions."""
	if frappe.db.exists("Role", MANAGER_ROLE):
		return

	frappe.get_doc(
		{
			"doctype": "Role",
			"role_name": MANAGER_ROLE,
			"desk_access": 1,
		}
	).insert(ignore_permissions=True)


def sync_feishu_managers():
	"""Explicitly synchronize active Project Member manager flags to Frappe roles."""
	ensure_manager_role()
	members = frappe.get_all(
		"Project Member",
		filters={"is_active": 1},
		fields=["email", "mobile", "user_id", "is_manager"],
	)

	for member in members:
		user_name = member.user_id or member.email or (f"{member.mobile}@juzi.com" if member.mobile else None)
		if not user_name or not frappe.db.exists("User", user_name):
			continue

		user = frappe.get_doc("User", user_name)
		has_role = any(row.role == MANAGER_ROLE for row in user.roles)
		if member.is_manager and not has_role:
			user.append("roles", {"role": MANAGER_ROLE})
			user.save(ignore_permissions=True)
		elif not member.is_manager and has_role and user.name != "Administrator":
			user.roles = [row for row in user.roles if row.role != MANAGER_ROLE]
			user.save(ignore_permissions=True)
