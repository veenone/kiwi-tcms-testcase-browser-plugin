from django.urls import reverse_lazy

# Follows the format of tcms.settings.common.MENU_ITEMS
# This will be added to the MORE menu automatically
MENU_ITEMS = [
    ("Test Browser", [
        ("Home", reverse_lazy("testbrowser-landing")),
        ("Test Case Browser", reverse_lazy("testcase-browser")),
        ("Test Plan Browser", reverse_lazy("testplan-browser")),
        ("Test Run Browser", reverse_lazy("testrun-browser")),
        ("Consolidated Browser", reverse_lazy("consolidated-browser")),
    ]),
]
