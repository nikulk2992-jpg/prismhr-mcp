"""Generic render primitives — EDI 834, flat-file, fixed-width.

Carrier-specific renderers compose these primitives with their companion-guide
config. Nothing in this module calls carrier-specific logic.
"""

from .edi_834 import Enrollment, Enrollee, Coverage, Render834

__all__ = ["Enrollment", "Enrollee", "Coverage", "Render834"]
