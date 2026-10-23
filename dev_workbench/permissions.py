# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _

MANAGER_ROLE = "Dev Workbench Manager"


def has_manager_access(user=None):
	"""Return whether a user may access Dev Workbench management features."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		return False
	if user == "Administrator":
		return True

	roles = frappe.get_roles(user)
	if "System Manager" in roles or MANAGER_ROLE in roles:
		return True

	member_filters = {"is_active": 1, "is_manager": 1}
	return bool(
		frappe.db.exists("Project Member", {**member_filters, "user_id": user})
		or frappe.db.exists("Project Member", {**member_filters, "email": user})
	)


def require_manager(message=None):
	"""Raise a permission error unless the current user is a workbench manager."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not has_manager_access():
		frappe.throw(
			message or _("Only Dev Workbench managers may perform this action."), frappe.PermissionError
		)


def has_app_permission():
	"""Permission callback used by Frappe's apps screen and app rail."""
	return has_manager_access()
