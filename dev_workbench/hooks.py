app_name = "dev_workbench"
app_title = "研发工作台"
app_publisher = "Company"
app_description = "研发工作台"
app_email = "admin@example.com"
app_license = "mit"

app_home = "/dev-workbench"
app_logo_url = "/assets/dev_workbench/logo.svg"

website_route_rules = [
	{"from_route": "/dev-workbench/<path:app_path>", "to_route": "dev_workbench_app"},
	{"from_route": "/dev-workbench", "to_route": "dev_workbench_app"},
]

add_to_apps_screen = [
	{
		"name": "dev_workbench",
		"logo": app_logo_url,
		"title": app_title,
		"route": app_home,
		"desk_route": "/app/研发工作台",
		"has_permission": "dev_workbench.permissions.has_app_permission",
	}
]

after_install = "dev_workbench.setup_roles.ensure_manager_role"

scheduler_events = {
    "daily": ["dev_workbench.services.review_cleanup.cleanup_reports"],
	"cron": {
		"*/30 * * * *": ["dev_workbench.tasks.sync.sync_codeup_data"],
		"0 18 * * 1-5": ["dev_workbench.tasks.absence.check_absence"],
		"0 9 * * 1-5": ["dev_workbench.tasks.report.push_daily_report"],
	}
}
