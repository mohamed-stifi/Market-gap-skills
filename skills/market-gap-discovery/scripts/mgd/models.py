"""Model tiers per subagent role, with escalation when a script check fails.

Most subagent output in this skill is machine-checked (quotes against snapshots, schemas,
screening and coding agreement), so those roles can run on a fast, cheap tier: a bad output is
caught and rejected, not trusted. Judgment-heavy roles (synthesis, red team, writing) get a
stronger tier. When a check fails for a role (quotes fail verification, a merge rejects many
records, agreement asks for a revision), that role is escalated one tier for its next assignment.
"""

from mgcore.jsonio import now_iso

from .common import protocol

TIERS = ["fast", "standard", "strong"]


def profile_name(run, c):
    return (protocol(run).get("cost_profile") or c.get("models.profile") or "balanced")


def tier_for(run, st, c, role):
    base = ((c.get("models.profiles") or {}).get(profile_name(run, c)) or {}).get(role, "standard")
    bump = int(((st.get("models") or {}).get("escalate") or {}).get(role, 0))
    return TIERS[min(len(TIERS) - 1, TIERS.index(base) + bump)]


def block(run, st, c, role):
    """The `model` field written into an assignment: tier plus the name each harness uses for it."""
    tier = tier_for(run, st, c, role)
    names = {h: m.get(tier) for h, m in (c.get("models.harness_names") or {}).items()}
    esc = int(((st.get("models") or {}).get("escalate") or {}).get(role, 0))
    return {"tier": tier, "profile": profile_name(run, c), "escalated": esc, "names": names}


def escalate(st, role, reason):
    """Raise `role` one tier for its next assignments (at most to the strongest tier); log why."""
    m = st.setdefault("models", {})
    esc = m.setdefault("escalate", {})
    if esc.get(role, 0) >= len(TIERS) - 1:
        return False
    esc[role] = esc.get(role, 0) + 1
    m.setdefault("log", []).append({"at": now_iso(), "role": role, "reason": reason, "level": esc[role]})
    return True


def escalate_once(st, key, role, reason):
    """Escalate at most once per check event (`key`, e.g. 'verify-R02'), so re-running a check never double-bumps."""
    seen = st.setdefault("models", {}).setdefault("seen", [])
    if key in seen:
        return False
    seen.append(key)
    return escalate(st, role, reason)


def note(doc):
    """One NOTE line for `next` describing the model a SPAWN should use."""
    mb = doc.get("model") or {}
    if not mb:
        return None
    names = mb.get("names") or {}
    cc = names.get("claude-code")
    return "model: %s tier%s (profile %s%s) -- pass it to the subagent call; see references/portability.md" % (
        mb.get("tier"), (" = %s in Claude Code" % cc) if cc else "", mb.get("profile"),
        ", escalated after a failed check" if mb.get("escalated") else "")
