#!/usr/bin/env python3
"""
QMAgent - Quality Management Agent for News MCP

A simple detection script that analyzes code changes and creates
tasks for Claude Code Agent to execute documentation updates.
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Set

# Add project root to path
sys.path.insert(0, '/home/cytrex/news-mcp')

class QMAgent:
    """Quality Management Agent - Detection and Task Creation for Claude Code."""

    def __init__(self, project_root: str = "/home/cytrex/news-mcp"):
        self.project_root = Path(project_root)
        self.last_check_file = self.project_root / ".qmagent_last_check"
        self.tasks_file = self.project_root / ".qmagent_tasks.json"

        # Files that trigger documentation updates
        self.trigger_patterns = {
            "app/repositories/": {
                "priority": "high",
                "docs": ["README.md", "DEVELOPER_SETUP.md", "TESTING.md"],
                "reason": "Repository Pattern changes detected"
            },
            "app/utils/feature_flags.py": {
                "priority": "critical",
                "docs": ["MONITORING.md", "DEVELOPER_SETUP.md"],
                "reason": "Feature flag system changes"
            },
            "app/utils/shadow_compare.py": {
                "priority": "high",
                "docs": ["MONITORING.md", "TESTING.md"],
                "reason": "Shadow comparison system changes"
            },
            "app/utils/monitoring.py": {
                "priority": "medium",
                "docs": ["MONITORING.md"],
                "reason": "Monitoring system changes"
            },
            "app/api/": {
                "priority": "medium",
                "docs": ["README.md"],
                "reason": "API changes detected"
            },
            "app/main.py": {
                "priority": "medium",
                "docs": ["README.md"],
                "reason": "Main application changes"
            },
            "alembic/versions/": {
                "priority": "medium",
                "docs": ["README.md", "DEVELOPER_SETUP.md"],
                "reason": "Database schema changes"
            },
            "pyproject.toml": {
                "priority": "low",
                "docs": ["DEVELOPER_SETUP.md"],
                "reason": "Dependencies or project configuration changes"
            }
        }

    def get_last_check_time(self) -> datetime:
        """Get timestamp of last check."""
        if self.last_check_file.exists():
            try:
                timestamp = float(self.last_check_file.read_text().strip())
                return datetime.fromtimestamp(timestamp)
            except (ValueError, FileNotFoundError):
                pass
        # Default: check last 24 hours
        return datetime.now() - timedelta(hours=24)

    def update_last_check_time(self):
        """Update last check timestamp."""
        self.last_check_file.write_text(str(time.time()))

    def detect_changes(self, since: datetime) -> List[Dict]:
        """Detect changes in monitored files since given timestamp."""
        changes = []

        for pattern, config in self.trigger_patterns.items():
            if pattern.endswith("/"):
                # Directory pattern
                search_path = self.project_root / pattern.rstrip("/")
                if search_path.exists():
                    for file_path in search_path.rglob("*.py"):
                        if file_path.stat().st_mtime > since.timestamp():
                            changes.append({
                                "file": str(file_path.relative_to(self.project_root)),
                                "pattern": pattern,
                                "priority": config["priority"],
                                "docs_affected": config["docs"],
                                "reason": config["reason"],
                                "timestamp": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                            })
            else:
                # Specific file
                file_path = self.project_root / pattern
                if file_path.exists() and file_path.stat().st_mtime > since.timestamp():
                    changes.append({
                        "file": pattern,
                        "pattern": pattern,
                        "priority": config["priority"],
                        "docs_affected": config["docs"],
                        "reason": config["reason"],
                        "timestamp": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    })

        return changes

    def generate_claude_tasks(self, changes: List[Dict]) -> Dict:
        """Generate tasks for Claude Code Agent."""
        if not changes:
            return {
                "status": "no_changes",
                "message": "No documentation updates needed",
                "timestamp": datetime.now().isoformat(),
                "tasks": []
            }

        # Group by priority
        by_priority = {"critical": [], "high": [], "medium": [], "low": []}
        docs_affected = set()

        for change in changes:
            by_priority[change["priority"]].append(change)
            docs_affected.update(change["docs_affected"])

        # Generate task description
        task_description = "🤖 **QMAgent Documentation Update Request**\n\n"

        if by_priority["critical"]:
            task_description += "## 🚨 CRITICAL PRIORITY\n"
            for change in by_priority["critical"]:
                task_description += f"- **{change['reason']}** in `{change['file']}`\n"
                task_description += f"  📝 Update: {', '.join(change['docs_affected'])}\n\n"

        if by_priority["high"]:
            task_description += "## ⚡ HIGH PRIORITY\n"
            for change in by_priority["high"]:
                task_description += f"- **{change['reason']}** in `{change['file']}`\n"
                task_description += f"  📝 Update: {', '.join(change['docs_affected'])}\n\n"

        if by_priority["medium"]:
            task_description += "## 📝 MEDIUM PRIORITY\n"
            for change in by_priority["medium"]:
                task_description += f"- **{change['reason']}** in `{change['file']}`\n"
                task_description += f"  📝 Update: {', '.join(change['docs_affected'])}\n\n"

        if by_priority["low"]:
            task_description += "## 🔍 LOW PRIORITY\n"
            for change in by_priority["low"]:
                task_description += f"- **{change['reason']}** in `{change['file']}`\n"
                task_description += f"  📝 Update: {', '.join(change['docs_affected'])}\n\n"

        task_description += """
## 🎯 Instructions for Claude Code Agent

1. **Use TodoWrite** to track these documentation tasks
2. **Read the changed files** to understand what needs documenting
3. **Update documentation** with current information:
   - Repository Pattern implementation details
   - Feature flag usage and monitoring
   - API changes and examples
   - Setup and testing procedures
4. **Focus on Repository Migration** - ensure all migration-related changes are documented
5. **Validate cross-references** between documentation files
6. **Mark tasks completed** in TodoWrite when done

## 📋 Specific Focus Areas
- Repository Pattern vs Raw SQL migration status
- Feature flag rollout percentages and monitoring
- Shadow comparison results and procedures
- Performance monitoring and SLOs
- Developer setup and testing workflows

**Priority:** Handle CRITICAL and HIGH priority items first.
"""

        return {
            "status": "tasks_available",
            "message": f"Found {len(changes)} changes requiring documentation updates",
            "timestamp": datetime.now().isoformat(),
            "priority_summary": {
                "critical": len(by_priority["critical"]),
                "high": len(by_priority["high"]),
                "medium": len(by_priority["medium"]),
                "low": len(by_priority["low"])
            },
            "docs_affected": list(docs_affected),
            "task_description": task_description,
            "changes": changes
        }

    def save_tasks(self, tasks: Dict):
        """Save tasks to file for Claude Code Agent."""
        self.tasks_file.write_text(json.dumps(tasks, indent=2))

    def load_tasks(self) -> Dict:
        """Load existing tasks."""
        if self.tasks_file.exists():
            try:
                return json.loads(self.tasks_file.read_text())
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        return {"status": "no_tasks", "tasks": []}

    def clear_tasks(self):
        """Clear completed tasks."""
        if self.tasks_file.exists():
            self.tasks_file.unlink()

    def run_check(self) -> str:
        """Run documentation check and return summary."""
        print("🔍 QMAgent: Checking for documentation updates needed...")

        # Get last check time
        last_check = self.get_last_check_time()
        print(f"📅 Checking changes since: {last_check.strftime('%Y-%m-%d %H:%M:%S')}")

        # Detect changes
        changes = self.detect_changes(last_check)
        print(f"🔍 Found {len(changes)} relevant changes")

        # Generate tasks
        tasks = self.generate_claude_tasks(changes)

        # Save tasks
        self.save_tasks(tasks)

        # Update check time
        self.update_last_check_time()

        # Return summary
        if tasks["status"] == "no_changes":
            return "✅ QMAgent: No documentation updates needed"
        else:
            summary = f"📋 QMAgent: {tasks['message']}\n"
            summary += f"Priority breakdown: "
            summary += f"Critical: {tasks['priority_summary']['critical']}, "
            summary += f"High: {tasks['priority_summary']['high']}, "
            summary += f"Medium: {tasks['priority_summary']['medium']}, "
            summary += f"Low: {tasks['priority_summary']['low']}\n"
            summary += f"📁 Tasks saved to: {self.tasks_file}\n"
            summary += f"🤖 Run Claude Code Agent to execute documentation updates"
            return summary

    def status(self) -> str:
        """Get current status."""
        tasks = self.load_tasks()

        if tasks["status"] == "no_tasks" or tasks["status"] == "no_changes":
            return "✅ QMAgent: No pending documentation tasks"

        if tasks["status"] == "tasks_available":
            summary = f"📋 QMAgent: {tasks['message']}\n"
            summary += f"Created: {tasks['timestamp']}\n"
            summary += f"Affected docs: {', '.join(tasks['docs_affected'])}\n"
            summary += f"🤖 Run Claude Code Agent to execute updates"
            return summary

        return "❓ QMAgent: Unknown status"

    def show_tasks(self) -> str:
        """Show current tasks for Claude Code Agent."""
        tasks = self.load_tasks()

        if tasks["status"] == "no_tasks" or tasks["status"] == "no_changes":
            return "📋 No pending documentation tasks"

        if tasks["status"] == "tasks_available":
            return tasks["task_description"]

        return "❓ No tasks available"

def main():
    """CLI interface for QMAgent."""
    import argparse

    parser = argparse.ArgumentParser(description="QMAgent - Quality Management Agent")
    parser.add_argument("action", nargs="?", default="check",
                       choices=["check", "status", "tasks", "clear"],
                       help="Action to perform")

    args = parser.parse_args()

    agent = QMAgent()

    if args.action == "check":
        result = agent.run_check()
        print(result)

    elif args.action == "status":
        result = agent.status()
        print(result)

    elif args.action == "tasks":
        result = agent.show_tasks()
        print(result)

    elif args.action == "clear":
        agent.clear_tasks()
        print("✅ Tasks cleared")

if __name__ == "__main__":
    main()