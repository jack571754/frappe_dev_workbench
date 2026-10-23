# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from dev_workbench.permissions import MANAGER_ROLE


class ProjectMember(Document):
	def validate(self):
		self._dedupe_git_identities()
		self._populate_identity_details()

	def _dedupe_git_identities(self):
		seen = set()
		for row in self.git_identities or []:
			if not row.git_identity:
				continue
			if row.git_identity in seen:
				frappe.throw(_("Git 身份 {0} 在成员中重复添加").format(row.git_identity))
			seen.add(row.git_identity)

	def _populate_identity_details(self):
		for row in self.git_identities or []:
			if row.git_identity and frappe.db.exists("Git Identity", row.git_identity):
				ident_doc = frappe.get_cached_doc("Git Identity", row.git_identity)
				row.identity = ident_doc.identity
				row.identity_type = ident_doc.identity_type
				row.status = "已认领"

	def on_update(self):
		if not getattr(self.flags, "from_git_identity_sync", False):
			self._sync_git_identities()
		self._sync_manager_role()

	def _sync_git_identities(self):
		linked_identities = [r.git_identity for r in self.git_identities or [] if r.git_identity]
		for ident_name in linked_identities:
			if frappe.db.exists("Git Identity", ident_name):
				ident_doc = frappe.get_doc("Git Identity", ident_name)
				if ident_doc.member != self.name or ident_doc.status != "已认领":
					ident_doc.member = self.name
					ident_doc.status = "已认领"
					if not ident_doc.claimed_at:
						ident_doc.claimed_at = now_datetime()
					if not ident_doc.claimed_by and frappe.session and frappe.session.user:
						ident_doc.claimed_by = frappe.session.user
					ident_doc.flags.ignore_permissions = True
					ident_doc.save()

	def _sync_manager_role(self):
		"""如果成员被标记为管理者，给对应的 Frappe User 赋予 Dev Workbench Manager 角色"""
		target_email = self.user_id or self.email
		if not target_email and self.mobile:
			target_email = f"{self.mobile}@juzi.com"

		if not target_email or not frappe.db.exists("User", target_email):
			return

		if not frappe.db.exists("Role", MANAGER_ROLE):
			return

		user = frappe.get_doc("User", target_email)
		has_role = any(r.role == MANAGER_ROLE for r in user.roles)

		if self.is_manager and not has_role:
			user.append("roles", {"role": MANAGER_ROLE})
			user.flags.ignore_permissions = True
			user.save()
		elif not self.is_manager and has_role and user.name != "Administrator":
			user.roles = [r for r in user.roles if r.role != MANAGER_ROLE]
			user.flags.ignore_permissions = True
			user.save()
