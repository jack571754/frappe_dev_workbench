# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

from frappe import _


def get_data():
	return [
		{
			"module_name": "Dev Workbench",
			"color": "#6366f1",
			"icon": "octicon octicon-git-commit",
			"type": "module",
			"label": _("研发工作台"),
			"link": "modules/Dev Workbench",
		}
	]
