from setuptools import find_packages
from setuptools import setup


setup(
    name="hyperion",
    description="Configuration tool for ML hyperparameter sweeps.",
    version="0.1.0",
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
    scripts=[
        "scripts/hyperion",
    ],
)
