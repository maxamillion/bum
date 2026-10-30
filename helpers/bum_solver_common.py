"""Shared RPM dependency conversion for libsolv-backed helpers."""
import solv

RPM_LESS = 2
RPM_GREATER = 4
RPM_EQUAL = 8
RELATION_MASK = RPM_LESS | RPM_GREATER | RPM_EQUAL


def rpm_relation(pool, name, relation, evr):
    """Build a supported relational dependency ID from normalized relation."""
    if relation not in {
        RPM_LESS, RPM_GREATER, RPM_EQUAL,
        RPM_LESS | RPM_EQUAL, RPM_GREATER | RPM_EQUAL,
    }:
        raise ValueError(f"unsupported RPM dependency relation for {name}")
    if not isinstance(evr, str) or not evr:
        raise ValueError(f"versioned RPM dependency {name} has no EVR")
    relation_flags = {
        RPM_LESS: solv.REL_LT,
        RPM_GREATER: solv.REL_GT,
        RPM_EQUAL: solv.REL_EQ,
        RPM_LESS | RPM_EQUAL: solv.REL_LT | solv.REL_EQ,
        RPM_GREATER | RPM_EQUAL: solv.REL_GT | solv.REL_EQ,
    }[relation]
    return pool.rel2id(
        pool.str2id(name, 1), pool.str2id(evr, 1), relation_flags
    )


def rpm_dependency(pool, name, flags, evr):
    """Convert RPM dependency fields to a libsolv dependency ID.

    The caller chooses whether to wrap the ID in ``pool.Dep`` or add it via
    ``add_deparray``. Non-version RPM flags are deliberately ignored here.
    """
    if not isinstance(name, str) or not name:
        raise ValueError("RPM dependency name must be a non-empty string")
    if not isinstance(flags, int) or isinstance(flags, bool) or flags < 0:
        raise ValueError(f"invalid RPM dependency flags for {name}")
    if evr is not None and (not isinstance(evr, str) or not evr):
        raise ValueError(f"invalid RPM dependency EVR for {name}")
    relation = flags & RELATION_MASK
    if not relation:
        return pool.str2id(name, 1)
    if not evr:
        raise ValueError(f"versioned RPM dependency {name} has no EVR")
    return rpm_relation(pool, name, relation, evr)
