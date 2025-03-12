# Import libraries
import os
import random

from config import TERRITORY_IMAGES_FOLDER, NUM_PLAYERS, territories_with_adjacency, continent_bonuses


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

# ----------------------------------------------------------------
# Board
# ----------------------------------------------------------------
class Board:
    def __init__(self, num_players=4):
        """Creates a board with all territories."""
        self.num_players = num_players
        self.territories = {name: Territory(name) for name in territories_with_adjacency}

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