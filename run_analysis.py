#!/usr/bin/env python3
"""
CLI script to run analysis batch job
Usage: python run_analysis.py [--limit 200] [--dry-run] [--verbose]
"""

import sys
import os

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.jobs.analysis_batch import main

if __name__ == "__main__":
    main()