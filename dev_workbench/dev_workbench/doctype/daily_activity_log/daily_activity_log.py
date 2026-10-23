# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class DailyActivityLog(Document):
	def validate(self):
		if not self.member:
			self.is_unclaimed = 1
		else:
			self.is_unclaimed = 0

		if not self.lines_unknown:
			self.total_lines = (self.lines_added or 0) + (self.lines_deleted or 0)
