from setuptools import setup, find_packages
import os

# Read the README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open(os.path.join(this_directory, 'requirements.txt'), encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="multi-arm-scheduling-agent",
    version="0.1.0",
    author="Multi-Arm Scheduling Agent Team",
    author_email="your.email@example.com",
    description="基于LLM与Harness Engineering的多机械臂调度智能体代码生成与仿真验证系统",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent",
    project_urls={
        "Bug Tracker": "https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent/issues",
        "Documentation": "https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent/docs",
        "Source Code": "https://github.com/L77Doncic/Multi-Arm-Scheduling-Agent",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Image Recognition",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "coverage>=7.3.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.7.0",
            "pylint>=3.0.0",
        ],
        "docs": [
            "sphinx>=7.0.0",
            "sphinx-rtd-theme>=1.3.0",
            "myst-parser>=2.0.0",
        ],
        "simulation": [
            # Isaac Sim / Omniverse dependencies
            # These need to be installed separately
        ],
    },
    entry_points={
        "console_scripts": [
            "multi-arm-agent=src.agent.core:main",
            "run-simulation=scripts.run_simulation:main",
            "evaluate=scripts.evaluate:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.md"],
    },
    keywords=[
        "robotics",
        "multi-arm",
        "scheduling",
        "llm",
        "harness-engineering",
        "isaac-sim",
        "simulation",
        "automation",
    ],
)
