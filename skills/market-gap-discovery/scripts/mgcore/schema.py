"""Minimal JSON Schema validator (the subset used by the skills' schemas).

Supported: type, enum, const, required, properties, additionalProperties, items, minItems,
maxItems, minLength, maxLength, pattern, minimum, maximum, format (date), anyOf, $ref
('#/$defs/name' within a schema, or another schema's $id resolved through a loader).
"""

import json
import os
import re

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SchemaRegistry(object):
    def __init__(self, *dirs):
        self.dirs = [d for d in dirs if d]
        self._cache = {}

    def load(self, name):
        if name in self._cache:
            return self._cache[name]
        for d in self.dirs:
            path = os.path.join(d, name + ".schema.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    schema = json.load(fh)
                self._cache[name] = schema
                return schema
        raise KeyError("schema not found: %s (looked in %s)" % (name, ", ".join(self.dirs)))


def _type_ok(value, t):
    if t == "object":
        return isinstance(value, dict)
    if t == "array":
        return isinstance(value, list)
    if t == "string":
        return isinstance(value, str)
    if t == "boolean":
        return isinstance(value, bool)
    if t == "null":
        return value is None
    if t == "integer":
        return (isinstance(value, int) and not isinstance(value, bool)) or (
            isinstance(value, float) and value.is_integer())
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def validate(instance, schema, registry=None, root=None, path="$"):
    """Return a list of error strings (empty when valid)."""
    errors = []
    root = root if root is not None else schema
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref.startswith("#/"):
            target = root
            for part in ref[2:].split("/"):
                target = target[part]
            return validate(instance, target, registry, root, path)
        if registry is None:
            return ["%s: cannot resolve $ref %s without a registry" % (path, ref)]
        target = registry.load(ref)
        return validate(instance, target, registry, target, path)
    if "anyOf" in schema:
        branch_errors = [validate(instance, s, registry, root, path) for s in schema["anyOf"]]
        if not any(len(b) == 0 for b in branch_errors):
            errors.append("%s: does not match any allowed shape" % path)
        return errors
    if "const" in schema and instance != schema["const"]:
        errors.append("%s: must equal %r" % (path, schema["const"]))
        return errors
    if "enum" in schema and instance not in schema["enum"]:
        errors.append("%s: %r is not one of %r" % (path, instance, schema["enum"]))
        return errors
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(instance, t) for t in types):
            errors.append("%s: expected %s, got %s" % (path, "/".join(types), type(instance).__name__))
            return errors
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append("%s: shorter than %d characters" % (path, schema["minLength"]))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append("%s: longer than %d characters (%d)" % (path, schema["maxLength"], len(instance)))
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append("%s: %r does not match %s" % (path, instance[:60], schema["pattern"]))
        if schema.get("format") == "date" and not _DATE.match(instance):
            errors.append("%s: not a YYYY-MM-DD date" % path)
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append("%s: below minimum %s" % (path, schema["minimum"]))
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append("%s: above maximum %s" % (path, schema["maximum"]))
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append("%s: needs at least %d items" % (path, schema["minItems"]))
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append("%s: allows at most %d items" % (path, schema["maxItems"]))
        if "items" in schema:
            for i, item in enumerate(instance):
                errors.extend(validate(item, schema["items"], registry, root, "%s[%d]" % (path, i)))
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append("%s: missing required field '%s'" % (path, key))
        props = schema.get("properties", {})
        for key, value in instance.items():
            if key in props:
                errors.extend(validate(value, props[key], registry, root, "%s.%s" % (path, key)))
            elif "additionalProperties" in schema:
                ap = schema["additionalProperties"]
                if ap is False:
                    errors.append("%s: unexpected field '%s'" % (path, key))
                elif isinstance(ap, dict):
                    errors.extend(validate(value, ap, registry, root, "%s.%s" % (path, key)))
    return errors
