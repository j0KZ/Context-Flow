"""
ContextFlow Python Package Setup
High-performance compression library with KB-scale memory footprint
"""

from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext
import sys
import os

# Version information
VERSION = "4.0.0"

# Read long description
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()


class CMakeExtension(Extension):
    def __init__(self, name, sourcedir=""):
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)


class CMakeBuild(build_ext):
    def run(self):
        # Build C library first if needed
        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        # Skip actual CMake build for pure Python implementation
        pass


setup(
    name="contextflow",
    version=VERSION,
    author="ContextFlow Team",
    author_email="support@contextflow.io",
    description="High-performance compression library with KB-scale memory footprint",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/contextflow",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Archiving :: Compression",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "xxhash>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "mypy>=1.0.0",
            "pylint>=2.15.0",
        ],
        "performance": [
            "numba>=0.58.0",
            "cython>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "contextflow=contextflow.cli:main",
        ],
    },
    ext_modules=[CMakeExtension("contextflow._c_extension")],
    cmdclass={"build_ext": CMakeBuild},
    zip_safe=False,
    include_package_data=True,
    package_data={
        "contextflow": ["*.dll", "*.so", "*.dylib"],
    },
)