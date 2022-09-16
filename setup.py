from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in client_registry/__init__.py
from client_registry import __version__ as version

setup(
	name="client_registry",
	version=version,
	description="Client Registry for healthcare systems",
	author="Lonius Limited",
	author_email="info@lonius.co.le",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
