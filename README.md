# RiftWii compatibility

This is the player-made list of how games run in RiftWii, the Wii homebrew game loader for Wii, GameCube and channel games on a Wii or a Wii U's vWii.

View the list: https://riftwii.github.io/compatibility.html

## How to report a game

1. Open the [Game report form](https://github.com/RiftWii/compatibility/issues/new?template=report.yml).
2. Fill in one report per game and setup. If you tried the same game on two consoles, file two reports.
3. Pick the status that fits best:
   - Perfect: no problems found.
   - Playable: small problems, but you can finish the game.
   - Has problems: big problems, crashes, or you cannot finish it.
   - Won't start: it never gets in-game.
4. Add where you got stuck or what worked, if you can.

Where to find things in RiftWii:

- Game ID: shown on the game's page in RiftWii. Wii and GameCube games have 6 characters (for example RMGE01). Channels have 4 (for example HAAA).
- cIOS: the d2x cIOS your games use, for example d2x v11 in slot 249. Leave it empty if you are unsure.
- RiftWii version: shown at the top of every Settings page, for example 2611-42.
- Problem report: you can send one from Settings > Help > Send a problem report, then paste the link in the form.

Please do not post personal info such as console IDs, friend codes or network names. CISO files are not supported; convert to ISO or RVZ in Dolphin first.

No GitHub account? A Discord route for sending reports is coming.

## What happens next

The list updates by itself within a few minutes of your report. Bad reports (spam, wrong game) are closed by a maintainer and drop out of the count. Results tested in Dolphin are kept apart from real consoles, so console results always come first.

## For maintainers

- Closing a report removes it from the list. Only open issues with the `report` label are counted.
- `data/dolphin.json` holds extra Dolphin results. It is a list of objects with `game_id`, `game_name`, `platform`, `status`, `version`, `notes` (optional) and `tested` (date string).
- Run the checks with `python -m unittest discover -s tests`. The build needs only the Python standard library, no npm and no build step.
