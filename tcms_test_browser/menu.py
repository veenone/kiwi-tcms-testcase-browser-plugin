from django.urls import reverse_lazy

# Follows the format of tcms.settings.common.MENU_ITEMS
# This will be added to the MORE menu automatically
MENU_ITEMS = [
    ("Test Case Browser", reverse_lazy("testcase-browser")),
]
