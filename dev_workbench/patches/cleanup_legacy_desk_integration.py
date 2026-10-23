import frappe


def execute():
	"""Remove UI records created by the retired runtime Desk integration."""
	for doctype, name in (
		("Page", "dev-workbench-page"),
		("Desktop Icon", "研发工作台"),
	):
		if frappe.db.exists("DocType", doctype) and frappe.db.exists(doctype, name):
			frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)

	if not frappe.db.exists("DocType", "Sidebar") or not frappe.db.exists("Sidebar", "研发工作台"):
		return

	sidebar = frappe.get_doc("Sidebar", "研发工作台")
	sidebar.set(
		"items",
		[
			item
			for item in sidebar.items
			if not (item.link_type == "Page" and item.link_to == "dev-workbench-page")
		],
	)
	sidebar.save(ignore_permissions=True)
