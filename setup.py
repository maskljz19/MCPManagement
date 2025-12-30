"""Setup script for MCP Platform Backend"""

from setuptools import setup, find_packages

setup(
    name="mcp-platform-backend",
    version="1.0.0",
    description="MCP Tool Management Platform Backend",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.23.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "sqlalchemy>=2.0.0",
        "alembic>=1.12.0",
        "motor>=3.3.0",
        "redis>=5.0.0",
        "celery>=5.3.0",
        "langchain>=0.1.0",
        "PyGithub>=2.0.0",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "prometheus-client>=0.18.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
        ]
    },
)
