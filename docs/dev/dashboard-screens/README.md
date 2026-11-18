# Dashboard screens

One screenshot per host dashboard page at desktop (1280 wide) and phone (500 wide, the narrowest headless Chrome draws; the tabs collapse below 700) width, made by `scripts/make-dashboard-screens.py` from simulated data. They follow the robot's settings pattern (`docs/design/screen-style.md`): a left column of tabs that scrolls on its own, a right pane that scrolls on its own, large rows, a clear active tab and Done in the same place; on a phone the tabs become a selector at the top in the same order.

Pages: Status (`/health`), On my robot (`/on-my-robot`), Brain (`/brain`). The main Settings page (`/settings`) is the existing single-page app and the Done link returns to it. Not yet in the shell: Robot software, Quiet hours and Games (not built), and Family and safety (a card inside Settings).
