"""Configuration: defaults.json ({value, source} leaves) overlaid with protocol overrides.

Overrides may be flat ("landscape.coverage_target": 0.97) or nested
({"landscape": {"coverage_target": 0.97}}); protocol.budget.* also overrides budget.*.
"""

from .jsonio import read_json


def _flatten(prefix, node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            _flatten(prefix + "." + k if prefix else k, v, out)
    else:
        out[prefix] = node


def leaves(defaults):
    """Yield (path, node) for every {value, source} leaf."""
    out = []

    def walk(prefix, node):
        if isinstance(node, dict) and "value" in node:
            out.append((prefix, node))
        elif isinstance(node, dict):
            for k, v in node.items():
                if k.startswith("_"):
                    continue
                walk(prefix + "." + k if prefix else k, v)
    walk("", defaults)
    return out


class Config(object):
    def __init__(self, defaults_path, protocol=None):
        self.defaults = read_json(defaults_path, {}) or {}
        self.protocol = protocol or {}
        flat = {}
        for k, v in (self.protocol.get("overrides") or {}).items():
            if isinstance(v, dict):
                _flatten(k, v, flat)
            else:
                flat[k] = v
        for k, v in (self.protocol.get("budget") or {}).items():
            flat.setdefault("budget." + k, v)
        self.overrides = flat

    def get(self, key, fallback=None):
        if key in self.overrides:
            return self.overrides[key]
        node = self.defaults
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return fallback
            node = node[part]
        if isinstance(node, dict) and "value" in node:
            return node["value"]
        return node

    def source(self, key):
        node = self.defaults
        for part in key.split("."):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        if key in self.overrides:
            return "protocol override"
        return node.get("source") if isinstance(node, dict) else None
