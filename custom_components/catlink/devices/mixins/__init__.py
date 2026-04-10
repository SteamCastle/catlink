"""Device mixins for CatLink integration."""

from .cat_discovery import CatDiscoveryMixin
from .logs import LogsMixin

__all__ = [
    "CatDiscoveryMixin",
    "LogsMixin",
]
