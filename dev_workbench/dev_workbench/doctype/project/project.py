# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Project(Document):
	def validate(self):
		self._validate_unique_repositories()

	def _validate_unique_repositories(self):
		seen = set()
		for row in self.project_repositories or []:
			if not row.repository:
				continue
			if row.repository in seen:
				frappe.throw(_("代码仓库 {0} 在该项目中重复添加").format(row.repository))
			seen.add(row.repository)
