import frappe


TARGETS = ["Payables", "Receivables", "Tools", "应付账款", "应收账款", "工具"]
FALLBACKS = {
    "Payables": ("DocType", "Purchase Invoice"),
    "应付账款": ("DocType", "Purchase Invoice"),
    "Receivables": ("DocType", "Sales Invoice"),
    "应收账款": ("DocType", "Sales Invoice"),
    "Tools": ("Page", "Workspace"),
    "工具": ("Page", "Workspace"),
}


def _link_exists(link_type: str, link_to: str) -> bool:
    if not link_type or not link_to:
        return False
    if link_type in ("DocType", "Page", "Report", "Workspace"):
        return bool(frappe.db.exists(link_type, link_to))
    if link_type in ("URL",):
        return True
    return True


def main():
    frappe.init(site="frontend")
    frappe.connect()
    changed = []
    skipped = []

    try:
        for name in TARGETS:
            if not frappe.db.exists("Workspace", name):
                continue

            ws = frappe.get_doc("Workspace", name)
            old_links = list(ws.links or [])

            valid_links = []
            for row in old_links:
                if row.type != "Link":
                    valid_links.append(row)
                    continue
                if _link_exists((row.link_type or "").strip(), (row.link_to or "").strip()):
                    valid_links.append(row)

            has_route_link = any(
                r.type == "Link" and (r.link_type or "").strip() in ("DocType", "Page", "Report", "Workspace", "URL")
                for r in valid_links
            )

            if not has_route_link:
                fb_type, fb_to = FALLBACKS.get(name, ("Page", "Workspace"))
                if _link_exists(fb_type, fb_to):
                    valid_links.append(
                        frappe._dict(
                            {
                                "type": "Link",
                                "label": ws.label or name,
                                "link_type": fb_type,
                                "link_to": fb_to,
                                "hidden": 0,
                                "is_query_report": 0,
                                "onboard": 0,
                                "link_count": 0,
                            }
                        )
                    )
                else:
                    skipped.append((name, f"fallback missing: {fb_type}/{fb_to}"))
                    continue

            ws.set("links", [])
            for row in valid_links:
                ws.append(
                    "links",
                    {
                        "type": row.type,
                        "label": getattr(row, "label", None),
                        "link_type": getattr(row, "link_type", None),
                        "link_to": getattr(row, "link_to", None),
                        "hidden": int(getattr(row, "hidden", 0) or 0),
                        "is_query_report": int(getattr(row, "is_query_report", 0) or 0),
                        "onboard": int(getattr(row, "onboard", 0) or 0),
                        "link_count": int(getattr(row, "link_count", 0) or 0),
                    },
                )

            ws.flags.ignore_links = True
            ws.save(ignore_permissions=True)
            changed.append(name)

        frappe.db.commit()
        frappe.clear_cache()

        print("CHANGED:", ", ".join(changed) if changed else "none")
        if skipped:
            print("SKIPPED:")
            for item in skipped:
                print(" -", item[0], item[1])
    finally:
        frappe.destroy()


def diagnose():
    frappe.init(site="frontend")
    frappe.connect()
    try:
        rows = frappe.get_all(
            "Workspace",
            fields=["name", "label", "module", "public", "is_hidden", "for_user", "link_type", "link_to"],
            order_by="module asc, label asc",
            limit_page_length=1000,
        )
        print("=== Workspace Overview ===")
        for r in rows:
            text = " ".join(
                [
                    (r.get("name") or "").lower(),
                    (r.get("label") or "").lower(),
                    (r.get("module") or "").lower(),
                ]
            )
            if any(k in text for k in ["payable", "receivable", "tool", "account"]):
                print("name={name}, label={label}, module={module}, link_type={link_type}, link_to={link_to}".format(**r))
    finally:
        frappe.destroy()


def fix_sidebar_routes():
    frappe.init(site="frontend")
    frappe.connect()
    changed = []
    try:
        sidebars = frappe.get_all("Workspace Sidebar", fields=["name", "title"], limit_page_length=1000)
        for s in sidebars:
            doc = frappe.get_doc("Workspace Sidebar", s.name)
            items = list(doc.items or [])

            valid = []
            for it in items:
                if it.type != "Link":
                    valid.append(it)
                    continue
                lt = (it.link_type or "").strip()
                to = (it.link_to or "").strip()
                ok = _link_exists(lt, to)
                if ok:
                    valid.append(it)

            has_valid_link = any(i.type == "Link" for i in valid)
            if not has_valid_link and doc.title and frappe.db.exists("Workspace", doc.title):
                valid.insert(
                    0,
                    frappe._dict(
                        {
                            "type": "Link",
                            "label": "Home",
                            "link_type": "Workspace",
                            "link_to": doc.title,
                            "idx": 0,
                        }
                    ),
                )

            if len(valid) != len(items) or (not items and valid):
                doc.set("items", [])
                idx = 1
                for i in valid:
                    doc.append(
                        "items",
                        {
                            "type": i.type,
                            "label": getattr(i, "label", None),
                            "link_type": getattr(i, "link_type", None),
                            "link_to": getattr(i, "link_to", None),
                            "url": getattr(i, "url", None),
                            "idx": idx,
                        },
                    )
                    idx += 1
                doc.save(ignore_permissions=True)
                changed.append(doc.title or doc.name)

        frappe.db.commit()
        frappe.clear_cache()
        print("SIDEBAR_CHANGED:", ", ".join(changed) if changed else "none")
    finally:
        frappe.destroy()


if __name__ == "__main__":
    main()
