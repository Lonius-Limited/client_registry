from . import __version__ as app_version

app_name = "client_registry"
app_title = "Client Registry"
app_publisher = "Lonius Limited"
app_description = "Client Registry for healthcare systems"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "info@lonius.co.le"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/client_registry/css/client_registry.css"
# app_include_js = "/assets/client_registry/js/client_registry.js"

# include js, css files in header of web template
# web_include_css = "/assets/client_registry/css/client_registry.css"
# web_include_js = "/assets/client_registry/js/client_registry.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "client_registry/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "client_registry.install.before_install"
# after_install = "client_registry.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "client_registry.uninstall.before_uninstall"
# after_uninstall = "client_registry.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "client_registry.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }
after_migrate =["client_registry.execute"]
# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Client Registry": {
		"before_save": ["client_registry.api.hie_registry.update_dependants","client_registry.api.hie_registry.update_full_name"],
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"client_registry.tasks.all"
# 	],
# 	"daily": [
# 		"client_registry.tasks.daily"
# 	],
# 	"hourly": [
# 		"client_registry.tasks.hourly"
# 	],
# 	"weekly": [
# 		"client_registry.tasks.weekly"
# 	]
# 	"monthly": [
# 		"client_registry.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "client_registry.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "client_registry.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "client_registry.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"client_registry.auth.validate"
# ]

# Translation
# --------------------------------

# Make link fields search translated document names for these DocTypes
# Recommended only for DocTypes which have limited documents with untranslated names
# For example: Role, Gender, etc.
# translated_search_doctypes = []
website_route_rules = [
	{
		"from_route": "/frontend/<path:app_path>",
		"to_route": "frontend",
	},
]
