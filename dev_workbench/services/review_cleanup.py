import frappe
from frappe.utils import add_to_date, now_datetime


def cleanup_reports():
    """按配置清理已结束任务；只处理本板块记录。"""
    days = max(1, int(frappe.conf.get('review_retention_days') or 90))
    cutoff = add_to_date(now_datetime(), days=-days)
    tasks = frappe.get_all('Code Review Task', filters={'status': ['not in', ['queued', 'preparing', 'running']],
        'modified': ['<', cutoff]}, pluck='name', limit_page_length=100)
    for name in tasks:
        # 按创建者最后复核/重试修改时间保留，防止刚复核的老任务被清理。
        frappe.db.sql('select name from `tabCode Review Task` where name=%s for update', name)
        doc = frappe.get_doc('Code Review Task', name)
        if doc.status in ('queued', 'preparing', 'running') or doc.modified >= cutoff:
            continue
        frappe.db.delete('Code Review Finding', {'task': name})
        frappe.db.set_value('Code Review Task', name, 'current_attempt', None)
        frappe.db.delete('Code Review Attempt', {'task': name})
        frappe.db.delete('Code Review Task', {'name': name})
