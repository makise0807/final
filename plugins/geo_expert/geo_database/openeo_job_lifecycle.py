"""Lifecycle states for future OpenEO job submission."""

from __future__ import annotations


OPENEO_JOB_LIFECYCLE_STATES = [
    "draft",
    "previewed",
    "validated",
    "awaiting_approval",
    "approved",
    "submit_blocked",
    "submit_unsupported",
    "submitted",
    "queued",
    "running",
    "finished",
    "failed",
    "cancelled",
]

