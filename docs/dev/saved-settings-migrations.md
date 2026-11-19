# Saved settings that move when a default changes

A saved value that equals an old default is moved to the new default; a value the owner chose stays. One row per migration (firmware track).

| Setting | Old default | New default | Patch | Rule |
|---|---|---|---|---|
| Quick actions list (`mp_pages`, key A) | beep, dance, game | beep, dance, camera (vision), say hi | SF101 | Only the exact old list moves. An owner who chose the same three sees the new default once and can pick again. |
| Control sheet timeout (`S`) saved under 8 s | 5 to 7 s | 8 s | UI01 | Raised to the new shortest. |
