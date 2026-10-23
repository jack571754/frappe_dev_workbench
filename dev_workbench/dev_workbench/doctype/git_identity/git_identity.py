# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class GitIdentity(Document):
	def validate(self):
		if self.identity:
			self.identity = self.identity.strip()

		if self.member:
			self.status = "已认领"
			if not self.claimed_at:
				self.claimed_at = now_datetime()
			if not self.claimed_by and frappe.session and frappe.session.user:
				self.claimed_by = frappe.session.user
		else:
			self.status = "待认领"
			self.claimed_at = None
			self.claimed_by = None

	def on_update(self):
		self._sync_with_member()

	def _sync_with_member(self):
		# Sync into Project Member child table if member is set
		if self.member and frappe.db.exists("Project Member", self.member):
			member_doc = frappe.get_doc("Project Member", self.member)
			existing_identities = [r.git_identity for r in member_doc.git_identities or []]
			if self.name not in existing_identities:
				member_doc.append(
					"git_identities",
					{
						"git_identity": self.name,
						"identity": self.identity,
						"identity_type": self.identity_type,
						"status": self.status,
					},
				)
				member_doc.flags.ignore_permissions = True
				member_doc.flags.from_git_identity_sync = True
				member_doc.save()
