"""memledger.registry: the Ed25519-signed company registry (slides 8, 9; I9, I10). Owner: M2."""

from memledger.registry.binding import bind_params, default_registry, set_default_registry
from memledger.registry.registry import ADMIN_ROLE, Registry, RegistryError, require_admin, sign_entries
from memledger.registry.schema import Entry, SchemaError

__all__ = ["ADMIN_ROLE", "Entry", "Registry", "RegistryError", "SchemaError", "bind_params", "default_registry",
           "require_admin", "set_default_registry", "sign_entries"]
