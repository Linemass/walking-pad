# Contributing

Thanks for helping. A few rules keep the app safe for the people who walk on it.

## Workflow

1. Branch from `main`: `feat/<short-name>` or `fix/<short-name>`.
2. Keep each pull request to one change. Describe what a user will notice.
3. Run the checks in the README's **Tests** table. The layout check must report `TOTAL 0`.
4. Open a pull request; the owner reviews and merges. Don't push to `main` directly.

## Rules

- **Never commit personal data or secrets**: `urevo.db`, `*.log`, account or device tokens, Cloudflare IDs or API
  tokens. Tests use `tests/fixtures/sample.db` (invented data). If you need new sample data, extend
  `tests/make_sample_db.py`.
- **Safety first with the pad.** Anything that can start the belt or raise the speed must go through
  `pad_control.py`, stay inside the pad's reported speed range, and keep the start countdown. Stop must always work.
- **Staging first.** Deploy to `--env staging` and try it before production. Production deploys are the owner's call.
- **Community data** stays daily totals only. Don't add fields that reveal where or exactly when someone walks.
- **No dark patterns.** No guilt copy, no punishing streak resets, at most one nudge a day. See the design notes in
  `design/`.
- **UI**: use the existing design system in `web/app.css` and the components in `web/ui.js`. No emojis in the UI;
  icons are SVG. Every new screen needs a scenario in `design/screens.html` so the layout check covers it.

## Where things are

See the README's **Folders** table and `AGENTS.md` (instructions for AI coding agents, also useful for people).
