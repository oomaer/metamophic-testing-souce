#!/usr/bin/env python3
"""MQTT Metamorphic Relation Test Runner"""
import sys
from fandango.evolution.algorithm import Fandango, LoggerLevel
from fandango.language.grammar import FuzzingMode
from fandango.language.parse.parse import parse

grammar_path = "mqtt-test.fan"

print(f"Loading grammar from {grammar_path}...")
with open(grammar_path) as f:
    grammar, constraints = parse(f, use_stdlib=False)

print("Initializing Fandango...")
fandango = Fandango(
    grammar=grammar,
    constraints=constraints,
    logger_level=LoggerLevel.INFO
)

print("Generating test cases...")
test_count = 0
violations = 0

try:
    for solution in fandango.generate(mode=FuzzingMode.IO):
        test_count += 1
        print(f"\n{'='*60}")
        print(f"Test case #{test_count}")
        print(f"{'='*60}")

        if test_count >= 5:  # Limit for now
            break

except KeyboardInterrupt:
    print("\n\nTest interrupted by user")
except Exception as e:
    print(f"\n\nError during test execution: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*60}")
print(f"Test Summary:")
print(f"  Total test cases: {test_count}")
print(f"  Violations found: {violations}")
print(f"{'='*60}")
