"""
Setup script for ContextFlow
"""

from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8') if (this_directory / "README.md").exists() else ""

setup(
    name="contextflow",
    version="1.0.0",
    author="ContextFlow Development",
    description="Advanced hybrid lossless compression system combining BWT, context modeling, neural mixing, and tANS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/contextflow/contextflow",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: System :: Archiving :: Compression",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.19.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.9",
        ],
        "benchmark": [
            "zstandard>=0.15",
        ]
    },
    entry_points={
        "console_scripts": [
            "contextflow=contextflow.cli:main",
        ],
    },
)