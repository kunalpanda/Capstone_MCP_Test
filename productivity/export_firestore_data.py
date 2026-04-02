#!/usr/bin/env python3
"""
Firestore Productivity Data Exporter
=====================================
Exports productivity_analysis events and workflow metadata from Firestore
into a single JSON file for use in the offline productivity dashboard.

Usage:
    cd Capstone_MCP_Test/productivity
    python export_firestore_data.py

Prerequisites:
    - google-cloud-firestore (pip install google-cloud-firestore)
    - Authenticated GCP credentials (gcloud auth application-default login)

Output:
    productivity_data.json  — ready to upload into the dashboard artifact
"""

import json
import os
import sys
from datetime import datetime

try:
    from google.cloud import firestore
except ImportError:
    print("❌ google-cloud-firestore not installed.")
    print("   Run: pip install google-cloud-firestore")
    sys.exit(1)


# ======================================
# Configuration
# ======================================
PROJECT_ID = os.getenv("PROJECT_ID", "capstone-cicd-ai")
OUTPUT_FILE = "productivity_data.json"


def export_productivity_events(db: firestore.Client) -> list:
    """
    Pull all productivity_analysis events from the 'events' collection.

    Each document has the shape:
    {
        "type": "productivity_analysis",
        "timestamp": "2026-03-29T01:26:39.370Z",
        "data": {
            "breakdown": { ... },
            "total_manual_minutes": 185,
            "total_manual_hours": 3.08,
            "ai_resolution_minutes": 12.3,
            "time_saved_minutes": 172.7,
            "hourly_rate": 75,
            "cost_saved": 231.25,
            "iteration_count": 8,
            "files_modified": 3
        }
    }
    """
    print(f"\n📥 Fetching productivity_analysis events...")

    events_ref = db.collection("events")

    # Pull ALL events and filter client-side to avoid needing a
    # composite Firestore index (type + timestamp).
    events = []
    total_scanned = 0
    for doc in events_ref.stream():
        total_scanned += 1
        data = doc.to_dict()
        if data.get("type") == "productivity_analysis":
            data["_doc_id"] = doc.id
            events.append(data)

    # Sort by timestamp ascending (oldest first)
    events.sort(key=lambda e: e.get("timestamp", ""))

    print(f"   Scanned {total_scanned} total events")
    print(f"   Found {len(events)} productivity_analysis events")
    return events


def export_workflow_metadata(db: firestore.Client) -> dict:
    """
    Pull all workflow documents for context (status, repo, branch, timestamps).

    Returns a dict keyed by workflow_id for easy lookup.
    """
    print(f"📥 Fetching workflow metadata...")

    workflows_ref = db.collection("workflows")
    workflows = {}

    for doc in workflows_ref.stream():
        data = doc.to_dict()
        # Convert Firestore timestamps to ISO strings for JSON serialization
        for key in ("createdAt", "updatedAt", "startedAt", "completedAt", "failedAt"):
            if key in data and data[key] is not None:
                try:
                    data[key] = data[key].isoformat()
                except (AttributeError, TypeError):
                    data[key] = str(data[key])

        # Handle nested result dict if it contains non-serializable types
        if "result" in data and isinstance(data["result"], list):
            data["result"] = f"[{len(data['result'])} messages]"

        workflows[doc.id] = data

    print(f"   Found {len(workflows)} workflow documents")
    return workflows


def export_all_events_summary(db: firestore.Client) -> dict:
    """
    Pull a summary of all event types for a given workflow to provide
    context (e.g., how many iterations, tool calls, etc.).

    Returns a dict keyed by event type with counts.
    """
    print(f"📥 Fetching event type summary...")

    events_ref = db.collection("events")
    type_counts = {}

    for doc in events_ref.stream():
        data = doc.to_dict()
        event_type = data.get("type", "unknown")
        type_counts[event_type] = type_counts.get(event_type, 0) + 1

    print(f"   Event type distribution:")
    for etype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"     {etype}: {count}")

    return type_counts


def main():
    print("=" * 60)
    print("📊 Firestore Productivity Data Exporter")
    print(f"   Project: {PROJECT_ID}")
    print("=" * 60)

    # Initialize Firestore client
    try:
        db = firestore.Client(project=PROJECT_ID)
        print(f"✅ Connected to Firestore ({PROJECT_ID})")
    except Exception as e:
        print(f"❌ Failed to connect to Firestore: {e}")
        print(f"\n💡 Make sure you're authenticated:")
        print(f"   gcloud auth application-default login")
        print(f"   gcloud config set project {PROJECT_ID}")
        sys.exit(1)

    # Export data
    productivity_events = export_productivity_events(db)
    workflow_metadata = export_workflow_metadata(db)
    event_summary = export_all_events_summary(db)

    # Build the output payload
    output = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "project_id": PROJECT_ID,
        "event_type_summary": event_summary,
        "workflow_count": len(workflow_metadata),
        "productivity_event_count": len(productivity_events),
        "workflows": workflow_metadata,
        "productivity_events": productivity_events,
    }

    # Write to file
    output_path = os.path.join(os.path.dirname(__file__), OUTPUT_FILE)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    file_size_kb = os.path.getsize(output_path) / 1024
    print(f"\n✅ Exported to: {output_path}")
    print(f"   File size: {file_size_kb:.1f} KB")
    print(f"   Productivity events: {len(productivity_events)}")
    print(f"   Workflows: {len(workflow_metadata)}")
    print(f"\n💡 Upload this file to Claude to build the dashboard.")


if __name__ == "__main__":
    main()
