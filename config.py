import os
import json

# ----------------------------------------------------------------
# File/Folder Constants
# ----------------------------------------------------------------

BOARD_FOLDER = "RiskBoard"
SCORED_GAMES = "ScoredGames"
GAME_REPLAY_STORAGE = "GameReplayStorage"
AI = "AI"
MISC_FOLDER = "Misc"
BACKGROUND_IMAGE_PATH = os.path.join(BOARD_FOLDER, "RiskMap.png")
TERRITORY_MAP_PATH = os.path.join(BOARD_FOLDER, "territory_map.json")
TERRITORY_IMAGES_FOLDER = os.path.join(BOARD_FOLDER, "territories")
mapjson = os.path.join(BOARD_FOLDER, "territory_map.json")
FONT_PATH = os.path.join(MISC_FOLDER, "FROMAN.TTF")

# Read and parse the territory_map.json file and put it into a dictionary
with open(mapjson, "r") as file:
    territory_positions = json.load(file)

CUSTOM_BOARDS_FOLDER = "CustomBoards"  # For saving/loading custom boards

SCREEN_WIDTH, SCREEN_HEIGHT = 1024, 656
PREVIEW_WIDTH, PREVIEW_HEIGHT = 400, 225  # mini UI preview

# Attempt to load territory positions
if not os.path.exists(TERRITORY_MAP_PATH):
    print(f"WARNING: {TERRITORY_MAP_PATH} not found.")
    territory_positions = {}
else:
    with open(TERRITORY_MAP_PATH, "r") as f:
        territory_positions = json.load(f)

# Define constants
NUM_TERRITORIES = 42  # Total number of territories
NUM_PLAYERS = 4       # Total number of players

REWARD_CONFIG = {
    "DEPLOY_BORDER": 5,
    "DEPLOY_2_BORDER": 10,
    "DEPLOY_SAFE": -2,
    "DEPLOY_COMPLETE_CONTINENT": 15,

    "ATTACK_WIN_TERRITORY": 20,
    "ATTACK_LEAVE_2_BORDER": 10,
    "ATTACK_HEAVY_LOSS": -15,
    "ATTACK_SKIPPED": -5,
    "ATTACK_ELIMINATE_PLAYER": 50,
    "ATTACK_COMPLETE_CONTINENT": 50,

    "FORTIFY_BORDER": 10,
    "FORTIFY_2_BORDER": 10,
    "FORTIFY_ABANDON_SAFE": 5,

    "GAME_WIN_MULTIPLIER": 1.25,
    "GAME_LOSE_MULTIPLIER": 0.85
}

# Information to build board, by tile and neighboring tiles
territories_with_adjacency = {
    "Alaska": ["Northwest_Territory", "Alberta", "Kamchatka"],
    "Northwest_Territory": ["Alaska", "Greenland", "Alberta", "Ontario"],
    "Alberta": ["Alaska", "Northwest_Territory", "Ontario", "Western_US"],
    "Ontario": ["Northwest_Territory", "Alberta", "Quebec", "Greenland", "Western_US", "Eastern_US"],
    "Greenland": ["Northwest_Territory", "Ontario", "Quebec", "Iceland"],
    "Quebec": ["Greenland", "Ontario", "Eastern_US"],
    "Eastern_US": ["Quebec", "Ontario", "Western_US", "Central_America"],
    "Western_US": ["Alberta", "Ontario", "Eastern_US", "Central_America"],
    "Central_America": ["Western_US", "Eastern_US", "Venezuela"],
    "Venezuela": ["Central_America", "Brazil", "Peru"],
    "Peru": ["Venezuela", "Brazil", "Argentina"],
    "Argentina": ["Peru", "Brazil"],
    "Brazil": ["Venezuela", "Peru", "Argentina", "North_Africa"],
    "North_Africa": ["Brazil","Western_Europe", "Southern_Europe", "Egypt", "East_Africa", "Congo"],
    "Egypt": ["North_Africa", "Southern_Europe", "Middle_East", "East_Africa"],
    "East_Africa": ["Egypt", "Middle_East", "Congo", "Madagascar", "South_Africa"],
    "Congo": ["North_Africa", "East_Africa", "South_Africa"],
    "South_Africa": ["Congo", "East_Africa", "Madagascar"],
    "Madagascar": ["East_Africa", "South_Africa"],
    "Western_Europe": ["North_Africa", "Southern_Europe", "Northern_Europe", "Great_Britain"],
    "Great_Britain": ["Iceland", "Scandinavia", "Northern_Europe", "Western_Europe"],
    "Iceland": ["Greenland", "Scandinavia", "Great_Britain"],
    "Scandinavia": ["Iceland", "Great_Britain", "Northern_Europe", "Ukraine"],
    "Northern_Europe": ["Western_Europe", "Great_Britain", "Scandinavia", "Ukraine", "Southern_Europe"],
    "Southern_Europe": ["Western_Europe", "Northern_Europe", "Ukraine", "North_Africa", "Egypt", "Middle_East"],
    "Ukraine": ["Scandinavia", "Northern_Europe", "Southern_Europe", "Middle_East", "Afghanistan", "Ural"],
    "Middle_East": ["Southern_Europe", "Egypt", "East_Africa", "Ukraine", "Afghanistan", "India"],
    "India": ["Middle_East", "Afghanistan", "China", "Siam"],
    "Siam": ["India", "China", "Indonesia"],
    "Indonesia": ["Siam", "New_Guinea", "Western_Australia"],
    "New_Guinea": ["Indonesia", "Western_Australia", "Eastern_Australia"],
    "Western_Australia": ["Indonesia", "New_Guinea", "Eastern_Australia"],
    "Eastern_Australia": ["Western_Australia", "New_Guinea"],
    "China": ["Siam", "India", "Afghanistan", "Ural", "Siberia", "Mongolia"],
    "Afghanistan": ["Ukraine", "Middle_East", "India", "Ural", "China"],
    "Ural": ["Ukraine", "Afghanistan", "China", "Siberia"],
    "Siberia": ["Ural", "China", "Mongolia", "Irkutsk", "Yakutsk"],
    "Mongolia": ["China", "Japan", "Kamchatka", "Irkutsk", "Siberia"],
    "Japan": ["Mongolia", "Kamchatka"],
    "Irkutsk": ["Siberia", "Yakutsk", "Kamchatka", "Mongolia"],
    "Yakutsk": ["Siberia", "Irkutsk", "Kamchatka"],
    "Kamchatka": ["Japan", "Irkutsk", "Yakutsk", "Mongolia", "Alaska"],
}

# Continents
continents = {
    "North America": ["Alaska", "Northwest_Territory", "Alberta", "Ontario", "Quebec", "Western_US", "Eastern_US", "Central_America", "Greenland"],
    "South America": ["Venezuela", "Brazil", "Peru", "Argentina"],
    "Europe": ["Iceland", "Great_Britain", "Western_Europe", "Northern_Europe", "Southern_Europe", "Ukraine", "Scandinavia"],
    "Africa": ["North_Africa", "Egypt", "East_Africa", "Congo", "South_Africa", "Madagascar"],
    "Asia": ["Middle_East", "Afghanistan", "India", "China", "Siberia", "Yakutsk", "Irkutsk", "Mongolia", "Kamchatka", "Japan", "Ural", "Siam"],
    "Australia": ["Indonesia", "New_Guinea", "Western_Australia", "Eastern_Australia"],
}

# Bonuses
continent_bonuses = {
    "North America": 5,
    "South America": 2,
    "Europe": 5,
    "Africa": 3,
    "Asia": 7,
    "Australia": 2,
}