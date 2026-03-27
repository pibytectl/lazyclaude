"""Generate screenshots of LazyClaude in various states."""

import asyncio
from pathlib import Path

from lazyclaude.app import LazyClaude

SCREENSHOT_DIR = Path(__file__).parent / "screenshots"


async def capture_screenshots():
    app = LazyClaude()

    async with app.run_test(size=(120, 40)) as pilot:
        # 1. Initial state — welcome screen
        await pilot.pause()
        app.save_screenshot(path=str(SCREENSHOT_DIR), filename="01_welcome.svg")

        # 2. Select first project (script)
        await pilot.press("enter")
        await pilot.pause()
        app.save_screenshot(path=str(SCREENSHOT_DIR), filename="02_project_loaded.svg")

        # 3. Switch to Config panel
        await pilot.press("2")
        await pilot.pause()
        app.save_screenshot(path=str(SCREENSHOT_DIR), filename="03_config_panel.svg")

        # 4. Switch to Memory panel
        await pilot.press("3")
        await pilot.pause()
        app.save_screenshot(path=str(SCREENSHOT_DIR), filename="04_memory_panel.svg")

        # 5. Switch to Skills panel
        await pilot.press("4")
        await pilot.pause()
        app.save_screenshot(path=str(SCREENSHOT_DIR), filename="05_skills_panel.svg")

        # 6. Switch to Agents panel
        await pilot.press("5")
        await pilot.pause()
        app.save_screenshot(path=str(SCREENSHOT_DIR), filename="06_agents_panel.svg")

        # 7. Switch to Sessions panel
        await pilot.press("6")
        await pilot.pause()
        app.save_screenshot(path=str(SCREENSHOT_DIR), filename="07_sessions_panel.svg")

        # 8. Help overlay
        await pilot.press("question_mark")
        await pilot.pause()
        app.save_screenshot(path=str(SCREENSHOT_DIR), filename="08_help_overlay.svg")


if __name__ == "__main__":
    asyncio.run(capture_screenshots())
