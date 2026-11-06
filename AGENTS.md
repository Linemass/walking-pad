# Walking Pad: agent instructions

Read `README.md` first. This file adds rules for AI coding agents (Claude Code, Codex, others).

- **One Bluetooth client.** The pad accepts a single connection, held by `urevo_logger.py`. Never add a second BLE
  client (a script, a browser Web Bluetooth page, a test) while the logger runs; it breaks logging.
- **Never touch the real database in tests.** Copy `tests/fixtures/sample.db` to a temp folder. The real
  `urevo.db` is the owner's history.
- **Never move the belt in tests.** Use the stub pattern in `design/test_controls.py` (replace
  `pad_control.command`). Only a human standing on the pad tests real start/speed.
- **Run Python with `-P`.** A stray file such as `select.py` in the working folder once shadowed the standard library.
- **Windows + Git Bash:** long heredocs break; write the script to a file and run it.
- **UI changes:** render with `design/render.py`, look at the screenshots, and keep `design/overlap_check.py` at
  `TOTAL 0` (it covers light + dark, desktop + phone, and checks that ring text stays inside the ring).
- **Engine changes:** keep `design/test_engine.py` passing; past days are judged by the goal that applied then
  (`goal_history`), so never recompute history with today's goal.
- **Cloud:** the account token lives only in the PC's settings table; phones get device tokens via pairing. Device
  tokens must not reach account-only endpoints (`accountOnly()` in `community/src/index.js`).
- **Deploys:** staging (`--env staging`) first; production only on the owner's say-so.
- **Secrets:** none in code, docs, logs or commits.
