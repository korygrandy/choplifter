#!/bin/bash
# Run all tests from the project root to ensure src package is importable
python -m pytest tests --disable-warnings
