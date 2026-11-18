"""Local memory for several adults as plain per-person notes files.

Remember and forget on request, and read back on request. One text file per person in the notes
folder, one note per line, readable and editable by hand. No database, no cloud, no recognition of
who is speaking (the person is named in robot.toml or chosen by the settings page); a child or teen
is never a notes person. What may be stored and who may read it is in `admission.py`.
"""

from maipai_packages.memory_notes.admission import AdmissionError, check_note
from maipai_packages.memory_notes.store import NotesStore, Notes

__all__ = ["AdmissionError", "Notes", "NotesStore", "check_note"]
