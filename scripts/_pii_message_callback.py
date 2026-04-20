"""Callback used by git-filter-repo to scrub tenant PII from commit
messages. Usage:

    git filter-repo --force --message-callback "$(cat scripts/_pii_message_callback.py)"
"""

# git-filter-repo passes `message` as bytes. We edit in place.
import re as _re

_BANNED = [
    b"Hardin", b"HARDIN", b"Bryan Hardin", b"BRYAN D",
    b"Salazar", b"Alberto Salazar",
    b"Peggy Clay", b"Rob Arlinghaus", b"Arlinghaus",
    b"Ashley Chance", b"Jason Sieg", b"Jennifer Gergen",
    b"Blake Bettey", b"Keith Puckett",
    b"Redkey", b"Phantom Neuro", b"Rise Community",
    b"Warren Professional", b"Joseph Michael Nunn",
    b"Simploy Outsourcing",
    b"M12853", b"X16702", b"F15198", b"G10567", b"R11296",
    b"A00025", b"E08645", b"E09317", b"A09313", b"H12272",
    b"H09176", b"Y11879", b"A05449", b"A05521",
]

_CLIENT_ID = _re.compile(rb"\b00[0-9]{4}\b")

for tok in _BANNED:
    message = message.replace(tok, b"<redacted>")
message = _CLIENT_ID.sub(b"<redacted>", message)
