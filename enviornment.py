# Import libraries
import os
import pickle
import random
import json
from config import GAME_REPLAY_STORAGE

from config import TERRITORY_IMAGES_FOLDER, NUM_PLAYERS, territories_with_adjacency, continent_bonuses

# ----------------------------------------------------------------
# Board
# ----------------------------------------------------------------
class Board:
    def __init__(self, num_players=4, player_ai_paths=None):
        """
        Initializes the board and loads AI models for each player.

        Args:
            num_players (int): Number of players in the game.
            player_ai_paths (dict): A dictionary mapping player numbers (1-4) to AI model paths.
        """
        self.num_players = num_players
        self.territories = {name: Territory(name) for name in territories_with_adjacency}

        # Ensure AI paths are mapped to correct players (default to None if missing)
        self.player_ai_paths = player_ai_paths if player_ai_paths else {i: None for i in range(1, num_players + 1)}

        # Load AI models for all players (including humans, if they have one)
        self.player_ai_models = self.load_ai_models()

        # Game Replay Tracking
        self.replay_file = os.path.join(GAME_REPLAY_STORAGE, "current_game_replay.json")
        self.game_replay = []  # Stores game history (for AI training & review)

    def load_ai_models(self):
        """
        Loads AI models from file paths. Each player gets their own AI.

        Returns:
            dict: {player_id: AI model}
        """
        ai_models = {}
        for player_id in range(1, self.num_players + 1):
            path = self.player_ai_paths.get(player_id)
            if path and os.path.exists(path):  # Load AI model if path exists
                with open(path, "rb") as f:
                    ai_models[player_id] = pickle.load(f)
            else:
                ai_models[player_id] = None  # No AI for this player

        return ai_models

    def get_territory(self, name):
        """Returns the Territory object by name."""
        return self.territories.get(name, None)

    def deploy_troops(self, player_id, territory, troops):
        """Adds troops to a valid territory."""
        target = self.get_territory(territory)
        if target and target.get_owner() == player_id:
            target.add_troops(troops)
            return True
        return False

    def calculate_troops(self, player_id):
        """Calculates the number of new troops a player gets."""
        territories_owned = sum(1 for t in self.territories.values() if t.owner == player_id)
        territory_bonus = max(territories_owned // 3, 3)

        continent_bonus = sum(
            continent_bonuses[cont] for cont, terrs in continent_bonuses.items()
            if all(self.territories[t].owner == player_id for t in terrs)
        )

        return territory_bonus + continent_bonus

    def check_winner(self):
        """Checks if there is a winner (one player owns all territories)."""
        owners = {t.owner for t in self.territories.values() if t.owner is not None}

        if len(owners) == 1:  # Only one player owns all territories
            return list(owners)[0]  # Return the winning player's ID

        return None  # No winner yet

    def generate_random_board(self):
        self.territories = Territory.create_territories_copy()
        territory_names = list(self.territories.keys())
        random.shuffle(territory_names)

        total = len(territory_names)
        base_count = total // self.num_players
        remainder = total % self.num_players

        idx = 0
        for player_id in range(1, self.num_players + 1):
            portion = base_count
            if remainder > 0:
                portion += 1
                remainder -= 1

            chunk = territory_names[idx : idx + portion]
            for name in chunk:
                self.territories[name].set_owner(player_id)
                self.territories[name].troop_count = 1
            idx += portion

    def generate_unowned_board(self):
        self.territories = Territory.create_territories_copy()
        for terr in self.territories.values():
            terr.set_owner(None)
            terr.troop_count = 0


# ----------------------------------------------------------------
# Territory
# ----------------------------------------------------------------
class Territory:
    """
    Represents a single territory with an owner (1..4 or None) and a troop count.
    Territory images are assumed to be white silhouettes on transparent backgrounds.
    """
    all_territories = {}

    def __init__(self, name):
        if name not in territories_with_adjacency:
            return
        self.name = name
        self.troop_count = 0
        self.owner = None
        self.image_path = os.path.join(TERRITORY_IMAGES_FOLDER, f"{name}.png")
        Territory.all_territories[name] = self

    def set_owner(self, player_id):
        if player_id is not None and not (1 <= player_id <= 4):
            raise ValueError("Invalid player ID.")
        self.owner = player_id

    def get_owner(self):
        return self.owner

    def get_image_path(self):
        return self.image_path

    @classmethod
    def initialize_territories(cls):
        for name in territories_with_adjacency:
            cls(name)

    @classmethod
    def create_territories_copy(cls):
        new_dict = {}
        for name in territories_with_adjacency:
            new_t = Territory(name)
            new_dict[name] = new_t
        return new_dict


Territory.initialize_territories()