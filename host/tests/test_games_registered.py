from pathlib import Path
import re


GAME_IDS = (
    "hilo",
    "reversi",
    "dicepoker",
    "battleship",
    "pong",
    "flyer",
    "balance",
    "maze",
)


def firmware_sources():
    root = Path(__file__).resolve().parents[2]
    candidates = [
        root / "firmware/main/hal/maipai_grid.cc",
        Path("/Users/jessetorres/esp/stackchan-rebuild/b87/firmware/main/hal/maipai_grid.cc"),
    ]
    for grid in candidates:
        if grid.is_file():
            return grid, grid.with_name("maipai_games.cc")
    raise AssertionError("Could not find firmware/main/hal/maipai_grid.cc")


def test_eight_games_are_registered_and_listed():
    grid_path, games_path = firmware_sources()
    grid = grid_path.read_text()
    games = games_path.read_text()

    table_match = re.search(r"const Info kInfo\[kKinds\] = \{(.*?)\n\};", grid, re.S)
    assert table_match, "Could not find the grid game kind table"
    table_ids = re.findall(r'\{"([a-z0-9]+)"\s*,', table_match.group(1))
    assert len(table_ids) == len(set(table_ids)), "The grid kind table contains a duplicate game id"
    for game_id in GAME_IDS:
        assert table_ids.count(game_id) == 1, f"{game_id} must appear exactly once in the grid kind table"

    list_text = games.split('mcp.AddTool("self.game.list"', 1)[1].split('mcp.AddTool("self.game.start"', 1)[0]
    start_text = games.split('mcp.AddTool("self.game.start"', 1)[1].split('mcp.AddTool("self.game.stop"', 1)[0]
    for game_id in GAME_IDS:
        assert game_id in list_text, f"{game_id} is missing from self.game.list tool text"
        assert game_id in start_text, f"{game_id} is missing from self.game.start tool text"
