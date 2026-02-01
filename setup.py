from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="kingnstar",
    version="0.1.3",
    author="Kingnstar Team",
    author_email="dev@kingnstar.com",
    description="A Git-like Version Control System in Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/kingnstar",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "kingnstar=kingnstar.cli:main",
        ],
    },
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Version Control",
    ],
    keywords="version control vcs git alternative",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/kingnstar/issues",
        "Source": "https://github.com/yourusername/kingnstar",
        "Documentation": "https://github.com/yourusername/kingnstar/wiki",
    },
)
