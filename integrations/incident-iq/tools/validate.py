#!/usr/bin/env python3
"""Validate the Incident iQ integration YAML files before uploading them.

Checks, for the integration definition and every action YAML:
  1. the file parses as YAML;
  2. each embedded script (`script.code` / `script.test_connection_code`)
     compiles as Python;
  3. consistency — every action's `integration` matches the definition `name`,
     every `--flag` a script reads maps to a declared field/data_attribute (or
     the platform-injected `proxy_url`), every declared field is consumed, and
     every `table_view` value references a declared `output` path.

Run from anywhere:  python3 tools/validate.py
Requires PyYAML (`pip install pyyaml`); exits non-zero if any check fails.
"""
import glob
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.stderr.write("This script needs PyYAML. Install it with: pip install pyyaml\n")
    sys.exit(2)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# proxy_url is injected by the platform when a proxy is configured; it is never
# declared as a field or data_attribute.
FRAMEWORK_VARS = {"proxy_url"}
VALID_ACTION_TYPES = {"Enrichment", "Containment", "Notification"}
VALID_FIELD_TYPES = {
    "text", "textarea", "number", "checkbox", "list", "multilist",
    "datetime", "tag", "upload", "fileDetonate",
}

failures = []


def fail(msg):
    failures.append(msg)
    print("  FAIL: " + msg)


def ok(msg):
    print("  ok:   " + msg)


def compiles(code, name):
    try:
        compile(code, name, "exec")
        ok("%s compiles" % name)
    except SyntaxError as exc:
        fail("%s syntax error: %s" % (name, exc))


def env_vars(code):
    return set(re.findall(r"add_argument\('--(\w+)'", code))


# --- integration definition ---
definition_path = os.path.join(ROOT, "incident-iq.yaml")
print("== " + os.path.relpath(definition_path, ROOT))
with open(definition_path) as handle:
    definition = yaml.safe_load(handle)

for key in ("name", "version", "icon", "script", "docker_repo_tag", "configuration"):
    if key in definition:
        ok("has key '%s'" % key)
    else:
        fail("missing key '%s'" % key)

data_attrs = set(definition.get("configuration", {}).get("data_attributes", {}).keys())
test_code = definition.get("script", {}).get("test_connection_code", "")
compiles(test_code, "test_connection_code")
missing = env_vars(test_code) - data_attrs - FRAMEWORK_VARS
if missing:
    fail("test_connection reads undeclared vars: %s" % sorted(missing))
else:
    ok("test_connection env vars all declared")
if not str(definition.get("icon", "")).startswith("data:image/png;base64,"):
    fail("icon is not a PNG data URI")

integration_name = definition.get("name")

# --- actions ---
for path in sorted(glob.glob(os.path.join(ROOT, "actions", "*.yaml"))):
    print("== " + os.path.relpath(path, ROOT))
    with open(path) as handle:
        action = yaml.safe_load(handle)

    if action.get("integration") == integration_name:
        ok("integration matches '%s'" % integration_name)
    else:
        fail("integration is %r, expected %r" % (action.get("integration"), integration_name))

    if action.get("type") in VALID_ACTION_TYPES:
        ok("type is %s" % action.get("type"))
    else:
        fail("invalid type: %r" % action.get("type"))

    code = action.get("script", {}).get("code", "")
    compiles(code, os.path.basename(path))

    field_ids = {f["id"] for f in action.get("fields", [])}
    script_vars = env_vars(code)
    missing = script_vars - field_ids - data_attrs - FRAMEWORK_VARS
    if missing:
        fail("script reads undeclared vars: %s" % sorted(missing))
    else:
        ok("script env vars all declared")
    unused = field_ids - script_vars
    if unused:
        fail("declared fields never read by script: %s" % sorted(unused))

    output_paths = {o["path"] for o in action.get("output", [])}
    dangling = {t["value"] for t in action.get("table_view", [])} - output_paths
    if dangling:
        fail("table_view references undeclared outputs: %s" % sorted(dangling))
    else:
        ok("table_view values all declared as outputs")

    for field in action.get("fields", []):
        if field.get("type") not in VALID_FIELD_TYPES:
            fail("field '%s' has invalid type %r" % (field.get("id"), field.get("type")))
        if field.get("type") == "list" and not field.get("values"):
            fail("list field '%s' has no values" % field.get("id"))

print()
if failures:
    print("%d failure(s)." % len(failures))
    sys.exit(1)
print("All checks passed.")
