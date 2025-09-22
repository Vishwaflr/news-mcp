#!/usr/bin/env python3
"""
Real-time monitoring dashboard for Repository Pattern migration.

This script provides a live console dashboard to monitor the repository migration
progress, feature flags, and performance metrics.
"""

import asyncio
import sys
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import requests
from dataclasses import dataclass

try:
    import curses
except ImportError:
    curses = None

# Configuration
API_BASE_URL = "http://localhost:8000"
REFRESH_INTERVAL = 2  # seconds
MAX_LOG_ENTRIES = 20


@dataclass
class DashboardData:
    """Container for dashboard data."""
    feature_flags: Dict[str, Any]
    shadow_comparison: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    health_status: Dict[str, Any]
    timestamp: datetime


class MonitoringDashboard:
    """Real-time monitoring dashboard for repository migration."""

    def __init__(self, api_base_url: str = API_BASE_URL):
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.session.timeout = 5
        self.running = True
        self.log_entries = []

    def fetch_data(self) -> Optional[DashboardData]:
        """Fetch all monitoring data from API."""
        try:
            # Fetch feature flags
            feature_flags = self._get("/api/admin/feature-flags/")

            # Fetch shadow comparison metrics
            shadow_comparison = self._get("/api/admin/feature-flags/metrics/shadow-comparison")

            # Fetch performance metrics
            performance_metrics = self._get("/api/admin/feature-flags/metrics/performance")

            # Fetch health status
            health_status = self._get("/api/health")

            return DashboardData(
                feature_flags=feature_flags,
                shadow_comparison=shadow_comparison,
                performance_metrics=performance_metrics,
                health_status=health_status,
                timestamp=datetime.now()
            )

        except Exception as e:
            self.log_error(f"Failed to fetch data: {e}")
            return None

    def _get(self, endpoint: str) -> Dict[str, Any]:
        """Make GET request to API endpoint."""
        url = f"{self.api_base_url}{endpoint}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def log_error(self, message: str):
        """Add error message to log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_entries.append(f"[{timestamp}] ERROR: {message}")
        if len(self.log_entries) > MAX_LOG_ENTRIES:
            self.log_entries.pop(0)

    def log_info(self, message: str):
        """Add info message to log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_entries.append(f"[{timestamp}] INFO: {message}")
        if len(self.log_entries) > MAX_LOG_ENTRIES:
            self.log_entries.pop(0)

    def format_console_output(self, data: DashboardData) -> str:
        """Format dashboard data for console output."""
        output = []

        # Header
        output.append("🎛️  REPOSITORY CUTOVER DASHBOARD")
        output.append("=" * 60)
        output.append(f"Last updated: {data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        output.append("")

        # Feature Flags
        output.append("📊 Feature Flags:")
        if data.feature_flags:
            for flag_name, flag_data in data.feature_flags.items():
                status = flag_data.get('status', 'unknown')
                rollout = flag_data.get('rollout_percentage', 0)
                output.append(f"  {flag_name}: {status} ({rollout}% rollout)")

                # Get metrics if available
                metrics = flag_data.get('metrics', {})
                if metrics:
                    success = metrics.get('success_count', 0)
                    errors = metrics.get('error_count', 0)
                    total = success + errors
                    error_rate = (errors / total * 100) if total > 0 else 0
                    output.append(f"    Success: {success:,}, Errors: {errors} ({error_rate:.1f}% error rate)")
        else:
            output.append("  No feature flags data available")

        output.append("")

        # Shadow Comparison
        output.append("🔍 Shadow Comparison:")
        if data.shadow_comparison:
            total = data.shadow_comparison.get('total_comparisons', 0)
            match_rate = data.shadow_comparison.get('match_rate', 0) * 100
            mismatches = data.shadow_comparison.get('mismatch_count', 0)
            errors = data.shadow_comparison.get('error_count', 0)

            output.append(f"  Total comparisons: {total:,}")
            output.append(f"  Match rate: {match_rate:.1f}%")
            output.append(f"  Mismatches: {mismatches}")
            output.append(f"  Errors: {errors}")

            # Performance comparison
            perf = data.shadow_comparison.get('performance', {})
            if perf:
                old_avg = perf.get('old_avg_ms', 0)
                new_avg = perf.get('new_avg_ms', 0)
                improvement = perf.get('improvement_percent', 0)
                output.append(f"  Performance: {old_avg:.1f}ms → {new_avg:.1f}ms ({improvement:+.1f}%)")
        else:
            output.append("  No shadow comparison data available")

        output.append("")

        # Performance Summary
        output.append("⏱️  Performance Summary:")
        if data.performance_metrics:
            for operation, metrics in data.performance_metrics.items():
                if isinstance(metrics, dict) and 'duration_stats' in metrics:
                    avg_ms = metrics['duration_stats'].get('avg_ms', 0)
                    p95_ms = metrics['duration_stats'].get('p95_ms', 0)
                    success_rate = metrics.get('success_rate', 0) * 100
                    output.append(f"  {operation}: {avg_ms:.1f}ms avg, {p95_ms:.1f}ms p95 ({success_rate:.1f}% success)")
        else:
            output.append("  No performance metrics available")

        output.append("")

        # Health Status
        output.append("🏥 System Health:")
        if data.health_status:
            status = data.health_status.get('status', 'unknown')
            output.append(f"  Overall status: {status}")

            components = data.health_status.get('components', {})
            for component, status_info in components.items():
                if isinstance(status_info, dict):
                    comp_status = status_info.get('status', 'unknown')
                    output.append(f"  {component}: {comp_status}")
                else:
                    output.append(f"  {component}: {status_info}")
        else:
            output.append("  No health data available")

        # Recent log entries
        if self.log_entries:
            output.append("")
            output.append("📝 Recent Events:")
            for entry in self.log_entries[-10:]:  # Show last 10 entries
                output.append(f"  {entry}")

        return "\n".join(output)

    def run_console(self):
        """Run dashboard in console mode (no curses)."""
        print("🎛️  Repository Migration Dashboard Starting...")
        print("Press Ctrl+C to exit")
        print()

        try:
            while self.running:
                # Clear screen
                print("\033[2J\033[H", end="")

                # Fetch and display data
                data = self.fetch_data()
                if data:
                    output = self.format_console_output(data)
                    print(output)
                else:
                    print("❌ Failed to fetch dashboard data")
                    print("Retrying in a few seconds...")

                # Wait for next refresh
                time.sleep(REFRESH_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n👋 Dashboard stopped by user")
            self.running = False

    def run_curses(self):
        """Run dashboard with curses interface."""
        if not curses:
            print("Curses not available, falling back to console mode")
            return self.run_console()

        def main_loop(stdscr):
            # Setup curses
            curses.curs_set(0)  # Hide cursor
            stdscr.nodelay(1)   # Non-blocking input

            try:
                while self.running:
                    # Clear screen
                    stdscr.clear()

                    # Fetch and display data
                    data = self.fetch_data()
                    if data:
                        output = self.format_console_output(data)
                        lines = output.split('\n')

                        max_y, max_x = stdscr.getmaxyx()
                        for i, line in enumerate(lines[:max_y-2]):
                            try:
                                stdscr.addstr(i, 0, line[:max_x-1])
                            except curses.error:
                                pass  # Ignore if line too long

                        # Add status line
                        status = f"Press 'q' to quit | Refreshing every {REFRESH_INTERVAL}s"
                        try:
                            stdscr.addstr(max_y-1, 0, status[:max_x-1], curses.A_REVERSE)
                        except curses.error:
                            pass
                    else:
                        stdscr.addstr(0, 0, "❌ Failed to fetch dashboard data")

                    stdscr.refresh()

                    # Check for input
                    key = stdscr.getch()
                    if key == ord('q') or key == ord('Q'):
                        break

                    # Wait for next refresh
                    time.sleep(REFRESH_INTERVAL)

            except KeyboardInterrupt:
                pass

        try:
            curses.wrapper(main_loop)
        except Exception as e:
            print(f"Curses error: {e}")
            print("Falling back to console mode")
            self.run_console()

    def run_single_check(self):
        """Run a single check and print results."""
        print("🎛️  Repository Migration Status Check")
        print("=" * 50)

        data = self.fetch_data()
        if data:
            output = self.format_console_output(data)
            print(output)
        else:
            print("❌ Failed to fetch dashboard data")
            return 1

        return 0


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Repository Migration Monitoring Dashboard")
    parser.add_argument("--api-url", default=API_BASE_URL,
                       help="API base URL (default: http://localhost:8000)")
    parser.add_argument("--refresh", type=int, default=REFRESH_INTERVAL,
                       help="Refresh interval in seconds (default: 2)")
    parser.add_argument("--mode", choices=["console", "curses", "check"], default="console",
                       help="Display mode (default: console)")

    args = parser.parse_args()

    # Update global settings
    global REFRESH_INTERVAL
    REFRESH_INTERVAL = args.refresh

    dashboard = MonitoringDashboard(args.api_url)

    if args.mode == "check":
        sys.exit(dashboard.run_single_check())
    elif args.mode == "curses":
        dashboard.run_curses()
    else:
        dashboard.run_console()


if __name__ == "__main__":
    main()