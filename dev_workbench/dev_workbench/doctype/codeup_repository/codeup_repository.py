# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

DEFAULT_EXCLUDE_RULES = """*.lock
package-lock.json
yarn.lock
pnpm-lock.yaml
dist/**
build/**
public/**
*.min.js
node_modules/**"""


class CodeupRepository(Document):
	def validate(self):
		if not self.exclude_rules:
			self.exclude_rules = DEFAULT_EXCLUDE_RULES
		if not self.default_branch:
			self.default_branch = "master"
