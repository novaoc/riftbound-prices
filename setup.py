from setuptools import setup, find_packages

setup(
    name="riftbound-prices",
    version="0.1.0",
    description="Riftbound TCG price tracker — single cards, sealed product & graded cards",
    author="novaoc",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "httpx>=0.25.0",
        "rich>=13.0.0",
        "beautifulsoup4>=4.12.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "mypy>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "riftbound-prices=riftbound_prices.cli:main",
        ],
    },
    python_requires=">=3.10",
)
