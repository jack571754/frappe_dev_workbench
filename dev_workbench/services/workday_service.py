# Copyright (c) 2026, Company and contributors
# For license information, please see license.txt

from datetime import date, datetime, timedelta

import frappe
from frappe import _

# 中国国家法定节假日与调休补班日历配置 (内置标准化日历，涵盖 2025/2026/2027)
# 调休上班日 (周末转工作日)
COMPENSATORY_WORKDAYS = {
	# 2025
	"2025-01-26",
	"2025-02-08",
	"2025-04-27",
	"2025-09-28",
	"2025-10-11",
	# 2026
	"2026-01-04",
	"2026-02-15",
	"2026-02-28",
	"2026-04-26",
	"2026-05-09",
	"2026-09-27",
	"2026-10-10",
	# 2027
	"2027-01-31",
	"2027-02-20",
	"2027-04-25",
	"2027-05-08",
	"2027-09-26",
	"2027-10-09",
}

# 法定放假日 (周一至周五转休假)
STATUTORY_HOLIDAYS = {
	# 2025
	"2025-01-01",
	"2025-01-28",
	"2025-01-29",
	"2025-01-30",
	"2025-01-31",
	"2025-02-03",
	"2025-02-04",
	"2025-04-04",
	"2025-05-01",
	"2025-05-02",
	"2025-05-05",
	"2025-05-31",
	"2025-10-01",
	"2025-10-02",
	"2025-10-03",
	"2025-10-06",
	"2025-10-07",
	"2025-10-08",
	# 2026
	"2026-01-01",
	"2026-01-02",
	"2026-02-16",
	"2026-02-17",
	"2026-02-18",
	"2026-02-19",
	"2026-02-20",
	"2026-04-06",
	"2026-05-01",
	"2026-05-04",
	"2026-05-05",
	"2026-06-19",
	"2026-09-25",
	"2026-10-01",
	"2026-10-02",
	"2026-10-05",
	"2026-10-06",
	"2026-10-07",
	# 2027
	"2027-01-01",
	"2027-02-05",
	"2027-02-08",
	"2027-02-09",
	"2027-02-10",
	"2027-04-05",
	"2027-05-03",
	"2027-06-09",
	"2027-09-15",
	"2027-10-01",
	"2027-10-04",
	"2027-10-05",
	"2027-10-06",
	"2027-10-07",
}


def to_date_obj(date_val) -> date:
	"""将各种类型的时间参数转换为 date 对象"""
	if isinstance(date_val, datetime):
		return date_val.date()
	if isinstance(date_val, date):
		return date_val
	raw = str(date_val).strip()[:10]
	return datetime.strptime(raw, "%Y-%m-%d").date()


def is_workday(date_val) -> bool:
	"""
	根据国家法定节假日与调休规则判定指定日期是否为工作日
	:param date_val: 日期字符串、date 或 datetime 对象
	:return: True 为工作日，False 为休息日
	"""
	d = to_date_obj(date_val)
	d_str = d.strftime("%Y-%m-%d")

	# 1. 优先判断调休补班（无论周末均算工作日）
	if d_str in COMPENSATORY_WORKDAYS:
		return True

	# 2. 判定国家法定节假日（平时调休放假均算休息日）
	if d_str in STATUTORY_HOLIDAYS:
		return False

	# 3. 正常周一至周五为工作日 (weekday: 0=周一, 4=周五)
	return d.weekday() < 5


def get_previous_workdays(ref_date, count: int = 2, include_ref_date: bool = False) -> list[str]:
	"""
	获取以 ref_date 为基准的前 count 个工作日列表（升序排列）
	:param ref_date: 基准参考日期
	:param count: 需获取的工作日天数（默认连续 2 个工作日）
	:param include_ref_date: 是否将 ref_date 本身纳入候选
	:return: 日期字符串列表 ['2026-10-13', '2026-10-14']
	"""
	curr = to_date_obj(ref_date)
	if not include_ref_date:
		curr -= timedelta(days=1)

	workdays = []
	# 往前回溯最多 30 天以防超长长假
	for _day_index in range(30):
		if is_workday(curr):
			workdays.append(curr.strftime("%Y-%m-%d"))
			if len(workdays) >= count:
				break
		curr -= timedelta(days=1)

	workdays.reverse()
	return workdays


def get_workdays_between(start_date, end_date) -> list[str]:
	"""
	获取指定闭区间 [start_date, end_date] 内的所有工作日
	"""
	s = to_date_obj(start_date)
	e = to_date_obj(end_date)
	if s > e:
		s, e = e, s

	result = []
	curr = s
	while curr <= e:
		if is_workday(curr):
			result.append(curr.strftime("%Y-%m-%d"))
		curr += timedelta(days=1)
	return result
