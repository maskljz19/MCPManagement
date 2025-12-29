#!/usr/bin/env python
"""
Database migration helper script.

Usage:
    python scripts/migrate.py create "migration message"  # Create new migration
    python scripts/migrate.py upgrade                      # Apply all migrations
    python scripts/migrate.py downgrade -1                 # Rollback one migration
    python scripts/migrate.py current                      # Show current revision
    python scripts/migrate.py history                      # Show migration history
"""

import sys
import subprocess
from pathlib import Path

# Ensure we're in the project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_alembic_command(args: list[str]) -> int:
    """Run an alembic command"""
    cmd = ["alembic"] + args
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 3:
            print("Error: Migration message required")
            print("Usage: python scripts/migrate.py create \"migration message\"")
            sys.exit(1)
        message = sys.argv[2]
        return run_alembic_command(["revision", "--autogenerate", "-m", message])
    
    elif command == "upgrade":
        target = sys.argv[2] if len(sys.argv) > 2 else "head"
        return run_alembic_command(["upgrade", target])
    
    elif command == "downgrade":
        target = sys.argv[2] if len(sys.argv) > 2 else "-1"
        return run_alembic_command(["downgrade", target])
    
    elif command == "current":
        return run_alembic_command(["current"])
    
    elif command == "history":
        return run_alembic_command(["history"])
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
