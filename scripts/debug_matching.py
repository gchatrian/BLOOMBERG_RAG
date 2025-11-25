#!/usr/bin/env python3
"""
DEBUG STUB MATCHING - Comprehensive Analysis

Traces the EXACT fingerprint generation at each step to find the mismatch.
NO Unicode characters - Windows compatible.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.stub.registry import StubRegistry
from src.models import EmailDocument, BloombergMetadata
from datetime import datetime
from config.settings import get_persistence_config

print("="*80)
print("STUB MATCHING DEBUG - COMPREHENSIVE ANALYSIS")
print("="*80)

# Load registry
config = get_persistence_config()
registry = StubRegistry(config.stub_registry_json)

pending = registry.get_all_pending()

if not pending:
    print("\nNo pending stubs found in registry!")
    sys.exit(0)

# Take first stub
stub = pending[0]

print(f"\n{'='*80}")
print("PART 1: STUB IN REGISTRY")
print(f"{'='*80}")
print(f"Subject: {stub.subject}")
print(f"Date: {stub.received_time}")
print(f"Fingerprint in registry: {stub.fingerprint}")

# Regenerate fingerprint using StubRegistry method
regenerated_fp = StubRegistry.create_fingerprint(stub.subject, stub.received_time)
print(f"Fingerprint regenerated: {regenerated_fp}")

if stub.fingerprint != regenerated_fp:
    print("WARNING: MISMATCH - Registry fingerprint differs from regenerated!")
else:
    print("OK: Registry fingerprint matches regenerated")

print(f"\n{'='*80}")
print("PART 2: SIMULATE COMPLETE EMAIL")
print(f"{'='*80}")

# Simulate a complete email with Bloomberg prefix
complete_subject = f"(BN) {stub.subject}"
complete_date = stub.received_time

print(f"Complete email subject: {complete_subject}")
print(f"Complete email date: {complete_date}")

# Method 1: Using StubRegistry.create_fingerprint()
fingerprint_method1 = StubRegistry.create_fingerprint(complete_subject, complete_date)
print(f"\nMethod 1 - StubRegistry.create_fingerprint():")
print(f"  Result: {fingerprint_method1}")

# Check if it would match
if fingerprint_method1 == stub.fingerprint:
    print("  OK: WOULD MATCH stub in registry!")
else:
    print("  ERROR: WOULD NOT MATCH stub in registry")

# Method 2: Using EmailDocument.get_fingerprint()
print(f"\nMethod 2 - EmailDocument.get_fingerprint():")

# Create a fake EmailDocument
metadata = BloombergMetadata(
    story_id=None,
    category="BN",
    author="Test"
)

email_doc = EmailDocument(
    outlook_entry_id="TEST123",
    subject=complete_subject,
    body="Test body",
    raw_body="Test body",
    sender="test@test.com",
    received_date=complete_date,
    bloomberg_metadata=metadata,
    status="complete",
    is_stub=False
)

# Get fingerprint from EmailDocument
fingerprint_method2 = email_doc.get_fingerprint()
print(f"  Result: {fingerprint_method2}")

if fingerprint_method2 == stub.fingerprint:
    print("  OK: WOULD MATCH stub in registry!")
else:
    print("  ERROR: WOULD NOT MATCH stub in registry")

print(f"\n{'='*80}")
print("PART 3: COMPARISON")
print(f"{'='*80}")
print(f"Stub fingerprint:                {stub.fingerprint}")
print(f"StubRegistry.create_fingerprint: {fingerprint_method1}")
print(f"EmailDocument.get_fingerprint:   {fingerprint_method2}")

print(f"\n{'='*80}")
print("PART 4: NORMALIZATION TEST")
print(f"{'='*80}")

print(f"\nOriginal stub subject: {stub.subject}")
normalized = StubRegistry.normalize_subject(stub.subject)
print(f"Normalized: {normalized}")

print(f"\nComplete email subject: {complete_subject}")
normalized_complete = StubRegistry.normalize_subject(complete_subject)
print(f"Normalized: {normalized_complete}")

if normalized == normalized_complete:
    print("\nOK: Normalization WORKS - subjects match after normalization")
else:
    print("\nERROR: Normalization FAILS - subjects don't match even after normalization")

print(f"\n{'='*80}")
print("DIAGNOSIS")
print(f"{'='*80}")

if fingerprint_method1 == fingerprint_method2:
    print("OK: Both methods generate the SAME fingerprint")
else:
    print("ERROR: Methods generate DIFFERENT fingerprints!")
    print("   >>> This is the problem - EmailDocument.get_fingerprint() doesn't use normalization")

if fingerprint_method1 == stub.fingerprint:
    print("OK: Matching SHOULD WORK if using StubRegistry.create_fingerprint()")
else:
    print("ERROR: Even StubRegistry.create_fingerprint() doesn't match registry")
    print("   >>> The stub registry was created before the fix")

print(f"\n{'='*80}")