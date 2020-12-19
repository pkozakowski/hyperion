from setuptools import find_packages
from setuptools import setup


setup(
    name="hyperion",
    description="hyperparameter sweeps on steroids",
    version="0.0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "gin-config",
        "lark",
    ],
    extras_require={
        "dev": [
            "black",
            "hypothesis",
            "pytest",
            "pytest-cov",
        ],
    },
)
