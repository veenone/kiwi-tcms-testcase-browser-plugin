import subprocess
import sys

from setuptools import setup
from setuptools.command.install import install


class PostInstallCommand(install):
    """Post-installation: run collectstatic to deploy plugin assets."""

    def run(self):
        install.run(self)
        try:
            subprocess.check_call(
                [sys.executable, "-m", "django", "collectstatic", "--noinput"],
            )
        except Exception:
            print(
                "NOTE: Run 'manage.py collectstatic' to deploy "
                "tcms-test-browser static files."
            )


setup(
    cmdclass={
        "install": PostInstallCommand,
    },
    data_files=[
        (
            "docs/screenshots",
            [
                "docs/screenshots/landing.png",
                "docs/screenshots/case_browser.png",
                "docs/screenshots/plan_browser.png",
                "docs/screenshots/run_browser.png",
                "docs/screenshots/consolidated_browser.png",
            ],
        ),
    ],
)
