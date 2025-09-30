#!/usr/bin/env python3
"""
Auto-Analysis Gradual Rollout Script

Manages the gradual rollout of the auto-analysis feature.
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.logging_config import get_logger
from app.services.auto_analysis_monitor import auto_analysis_monitor
from app.utils.feature_flags import feature_flags, FeatureFlagStatus
from sqlmodel import Session, select
from app.database import engine
from app.models.core import Feed

logger = get_logger(__name__)


class AutoAnalysisRolloutManager:
    """Manages the gradual rollout of auto-analysis feature."""

    def __init__(self):
        self.rollout_phases = [
            {
                "name": "Phase 1: Initial Canary",
                "percentage": 10,
                "min_observation_hours": 24,
                "success_criteria": {
                    "max_error_rate": 0.05,  # 5%
                    "min_runs": 10,
                    "max_daily_cost": 50.0
                }
            },
            {
                "name": "Phase 2: Extended Canary",
                "percentage": 25,
                "min_observation_hours": 48,
                "success_criteria": {
                    "max_error_rate": 0.05,
                    "min_runs": 25,
                    "max_daily_cost": 75.0
                }
            },
            {
                "name": "Phase 3: Half Rollout",
                "percentage": 50,
                "min_observation_hours": 72,
                "success_criteria": {
                    "max_error_rate": 0.03,
                    "min_runs": 50,
                    "max_daily_cost": 100.0
                }
            },
            {
                "name": "Phase 4: Wide Rollout",
                "percentage": 75,
                "min_observation_hours": 48,
                "success_criteria": {
                    "max_error_rate": 0.03,
                    "min_runs": 75,
                    "max_daily_cost": 125.0
                }
            },
            {
                "name": "Phase 5: Full Rollout",
                "percentage": 100,
                "min_observation_hours": 0,
                "success_criteria": {
                    "max_error_rate": 0.02,
                    "min_runs": 100,
                    "max_daily_cost": 150.0
                }
            }
        ]
        self.rollout_state_file = "rollout_state.json"

    def get_current_state(self) -> Dict[str, Any]:
        """Get the current rollout state."""
        if os.path.exists(self.rollout_state_file):
            with open(self.rollout_state_file, 'r') as f:
                return json.load(f)

        # Initialize state
        return {
            "current_phase": -1,  # Not started
            "phase_started_at": None,
            "rollback_count": 0,
            "history": []
        }

    def save_state(self, state: Dict[str, Any]):
        """Save the rollout state to file."""
        with open(self.rollout_state_file, 'w') as f:
            json.dump(state, f, indent=2, default=str)

    def check_phase_criteria(self, phase: Dict[str, Any]) -> tuple[bool, list]:
        """Check if current phase meets success criteria."""
        metrics = auto_analysis_monitor.get_system_metrics()
        criteria = phase["success_criteria"]
        issues = []

        # Check error rate
        if metrics.error_rate > criteria["max_error_rate"]:
            issues.append(f"Error rate {metrics.error_rate:.1%} exceeds threshold {criteria['max_error_rate']:.1%}")

        # Check minimum runs
        if metrics.total_runs_today < criteria["min_runs"]:
            issues.append(f"Only {metrics.total_runs_today} runs today, need {criteria['min_runs']}")

        # Check cost
        if metrics.estimated_cost_today > criteria["max_daily_cost"]:
            issues.append(f"Daily cost ${metrics.estimated_cost_today:.2f} exceeds ${criteria['max_daily_cost']}")

        return len(issues) == 0, issues

    def rollback(self, reason: str):
        """Rollback to previous phase."""
        state = self.get_current_state()
        current_phase = state["current_phase"]

        if current_phase > 0:
            previous_phase = self.rollout_phases[current_phase - 1]
            self.apply_phase(current_phase - 1)

            state["current_phase"] = current_phase - 1
            state["rollback_count"] += 1
            state["history"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "action": "rollback",
                "from_phase": current_phase,
                "to_phase": current_phase - 1,
                "reason": reason
            })
            self.save_state(state)

            logger.warning(f"Rolled back from phase {current_phase} to {current_phase - 1}: {reason}")
        else:
            # Disable completely
            feature_flags.set_flag_status("auto_analysis_global", FeatureFlagStatus.OFF, 0)
            logger.error(f"Rollback requested but already at phase 0, disabling feature: {reason}")

    def apply_phase(self, phase_index: int):
        """Apply a specific rollout phase."""
        if phase_index < 0 or phase_index >= len(self.rollout_phases):
            raise ValueError(f"Invalid phase index: {phase_index}")

        phase = self.rollout_phases[phase_index]
        percentage = phase["percentage"]

        # Determine status based on percentage
        if percentage == 0:
            status = FeatureFlagStatus.OFF
        elif percentage == 100:
            status = FeatureFlagStatus.ON
        else:
            status = FeatureFlagStatus.CANARY

        feature_flags.set_flag_status("auto_analysis_global", status, percentage)
        logger.info(f"Applied {phase['name']} with {percentage}% rollout")

    def advance_rollout(self) -> Dict[str, Any]:
        """Attempt to advance to the next rollout phase."""
        state = self.get_current_state()
        current_phase = state["current_phase"]

        # Check if we can advance
        if current_phase >= len(self.rollout_phases) - 1:
            return {
                "success": False,
                "message": "Already at final phase",
                "current_phase": current_phase
            }

        # If not started, begin with phase 0
        if current_phase == -1:
            next_phase = 0
            self.apply_phase(next_phase)

            state["current_phase"] = next_phase
            state["phase_started_at"] = datetime.utcnow().isoformat()
            state["history"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "action": "start",
                "phase": next_phase,
                "percentage": self.rollout_phases[next_phase]["percentage"]
            })
            self.save_state(state)

            return {
                "success": True,
                "message": f"Started rollout with {self.rollout_phases[next_phase]['name']}",
                "phase": next_phase,
                "percentage": self.rollout_phases[next_phase]["percentage"]
            }

        # Check observation period
        current_phase_config = self.rollout_phases[current_phase]
        phase_start = datetime.fromisoformat(state["phase_started_at"])
        hours_elapsed = (datetime.utcnow() - phase_start).total_seconds() / 3600

        if hours_elapsed < current_phase_config["min_observation_hours"]:
            hours_remaining = current_phase_config["min_observation_hours"] - hours_elapsed
            return {
                "success": False,
                "message": f"Need {hours_remaining:.1f} more hours of observation",
                "current_phase": current_phase,
                "hours_elapsed": hours_elapsed,
                "hours_required": current_phase_config["min_observation_hours"]
            }

        # Check success criteria
        meets_criteria, issues = self.check_phase_criteria(current_phase_config)

        if not meets_criteria:
            return {
                "success": False,
                "message": "Current phase does not meet success criteria",
                "current_phase": current_phase,
                "issues": issues
            }

        # Advance to next phase
        next_phase = current_phase + 1
        self.apply_phase(next_phase)

        state["current_phase"] = next_phase
        state["phase_started_at"] = datetime.utcnow().isoformat()
        state["history"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": "advance",
            "from_phase": current_phase,
            "to_phase": next_phase,
            "percentage": self.rollout_phases[next_phase]["percentage"]
        })
        self.save_state(state)

        return {
            "success": True,
            "message": f"Advanced to {self.rollout_phases[next_phase]['name']}",
            "phase": next_phase,
            "percentage": self.rollout_phases[next_phase]["percentage"]
        }

    def get_rollout_status(self) -> Dict[str, Any]:
        """Get detailed rollout status."""
        state = self.get_current_state()
        current_phase = state["current_phase"]

        if current_phase == -1:
            return {
                "status": "not_started",
                "message": "Rollout has not been started",
                "next_action": "Run 'start' to begin rollout"
            }

        current_phase_config = self.rollout_phases[current_phase]
        phase_start = datetime.fromisoformat(state["phase_started_at"])
        hours_elapsed = (datetime.utcnow() - phase_start).total_seconds() / 3600

        # Get metrics
        metrics = auto_analysis_monitor.get_system_metrics()
        meets_criteria, issues = self.check_phase_criteria(current_phase_config)

        # Get feed status
        with Session(engine) as session:
            total_feeds = session.exec(select(Feed)).all()
            enabled_feeds = [f for f in total_feeds if f.auto_analyze_enabled]
            rolled_out_feeds = [
                f for f in enabled_feeds
                if feature_flags.is_enabled("auto_analysis_global", str(f.id))
            ]

        return {
            "current_phase": {
                "index": current_phase,
                "name": current_phase_config["name"],
                "percentage": current_phase_config["percentage"],
                "started_at": phase_start.isoformat(),
                "hours_elapsed": round(hours_elapsed, 1),
                "hours_required": current_phase_config["min_observation_hours"]
            },
            "metrics": {
                "runs_today": metrics.total_runs_today,
                "error_rate": f"{metrics.error_rate:.1%}",
                "daily_cost": f"${metrics.estimated_cost_today:.2f}",
                "feeds_enabled": len(enabled_feeds),
                "feeds_rolled_out": len(rolled_out_feeds)
            },
            "criteria_check": {
                "meets_criteria": meets_criteria,
                "issues": issues
            },
            "rollback_count": state["rollback_count"],
            "can_advance": hours_elapsed >= current_phase_config["min_observation_hours"] and meets_criteria,
            "next_phase": self.rollout_phases[current_phase + 1]["name"] if current_phase < len(self.rollout_phases) - 1 else "Complete"
        }


def main():
    """Main rollout script."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage auto-analysis gradual rollout")
    parser.add_argument("command", choices=["status", "advance", "rollback", "start", "pause"],
                       help="Command to execute")
    parser.add_argument("--reason", help="Reason for rollback (required for rollback command)")
    parser.add_argument("--force", action="store_true", help="Force action even if criteria not met")

    args = parser.parse_args()

    manager = AutoAnalysisRolloutManager()

    if args.command == "status":
        status = manager.get_rollout_status()
        print(json.dumps(status, indent=2))

    elif args.command == "start":
        if manager.get_current_state()["current_phase"] != -1:
            print("Rollout already started")
            sys.exit(1)
        result = manager.advance_rollout()
        print(json.dumps(result, indent=2))

    elif args.command == "advance":
        result = manager.advance_rollout()
        if not result["success"] and args.force:
            # Force advance
            state = manager.get_current_state()
            next_phase = state["current_phase"] + 1
            if next_phase < len(manager.rollout_phases):
                manager.apply_phase(next_phase)
                state["current_phase"] = next_phase
                state["phase_started_at"] = datetime.utcnow().isoformat()
                state["history"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": "force_advance",
                    "phase": next_phase,
                    "percentage": manager.rollout_phases[next_phase]["percentage"]
                })
                manager.save_state(state)
                result = {
                    "success": True,
                    "message": f"Forced advance to phase {next_phase}",
                    "warning": "Criteria were not met, forced advance"
                }
        print(json.dumps(result, indent=2))

    elif args.command == "rollback":
        if not args.reason:
            print("--reason is required for rollback")
            sys.exit(1)
        manager.rollback(args.reason)
        print(f"Rolled back: {args.reason}")

    elif args.command == "pause":
        feature_flags.set_flag_status("auto_analysis_global", FeatureFlagStatus.OFF, 0)
        print("Auto-analysis paused (feature flag disabled)")


if __name__ == "__main__":
    main()