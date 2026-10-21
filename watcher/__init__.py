"""The Watcher: an AI entity that sees every run of the circuit and is sworn not to interfere.

It reads the record Warden writes at the end of a run and tells a person what happened, in
plain words. It has no authority. Warden, the Judge, Ghost Tools, SWIZZLE and the seats have no
input that comes from it; it cannot change a verdict, a finding, a file or a baseline. Every
sentence it keeps cites a measurement by id, and a sentence that cites nothing, cites something
that is not in the record, or makes a status claim of its own ("production ready") is dropped
before anyone reads it. That is the oath, and `watcher.oath` is the part of the code that keeps it.
"""

from __future__ import annotations

__version__ = "0.3.5"

#: The oath, as text. Printed at the end of every account so the reader knows what was promised.
OATH = (
    "The Watcher sees and does not interfere. It reads the run record and nothing else it was not "
    "shown. It writes nothing into the folder that was governed, nothing any instrument or seat reads, "
    "and nothing that changes a verdict. Every sentence it keeps cites a measurement in the record by "
    "id; a sentence that cites nothing, cites what is not there, or claims a status of its own is "
    "dropped before it is read. Its account is a description, never a grade."
)

__all__ = ["OATH", "__version__"]
