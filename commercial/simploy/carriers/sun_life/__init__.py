"""Sun Life EDX (Electronic Data Exchange) flat-file renderer.

Sun Life uses EDX — a pipe-delimited flat-file format for benefit
enrollment. This is NOT ANSI 834; EDX is Sun Life's proprietary
carrier-specific format, widely used across their group disability
+ voluntary benefit lines.

Reference: Sun Life EDX Implementation Guide (available to licensed
carrier partners).
"""

from .render import render_sun_life_edx

__all__ = ["render_sun_life_edx"]
