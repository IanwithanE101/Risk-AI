# Import libraries
import os
import pickle
import random
import json

import numpy as np

from config import GAME_REPLAY_STORAGE, territory_card_types, continents

from config import TERRITORY_IMAGES_FOLDER, NUM_PLAYERS, territories_with_adjacency, continent_bonuses

# ----------------------------------------------------------------
# Board
# ----------------------------------------------------------------
class Board:
    def __init__(self, ai_file_paths=None):
        """
        Initializes the board and loads AI models for each player.

        Args:
            ai_file_paths (list of str or None): A list of 4 AI model file paths (one per player).
        """
        self.num_players = NUM_PLAYERS  # Risk always has 4 players
        self.territories = {name: Territory(name) for name in territories_with_adjacency}
        self.cards = CardManager()  # New card system

        # Ensure AI file paths is a list of exactly 4 entries (default to None if missing)
        if ai_file_paths is None or len(ai_file_paths) != 4:
            self.ai_file_paths = [None] * 4
        else:
            self.ai_file_paths = ai_file_paths

        # Load AI models for all players (including humans, if they have one)
        self.player_ai_models = self.load_ai_models()

        # Game Replay Tracking
        self.replay_file = os.path.join(GAME_REPLAY_STORAGE, "current_game_replay.json")
        self.game_replay = []  # Stores game history (for AI training & review)

    def get_ai_file_paths(self):
        """
        Returns a list of AI model file paths for each player.

        Returns:
            list of str or None: AI file paths per player (index 0 = Player 1).
        """
        return self.ai_file_paths

    def load_ai_models(self):
        """Loads AI models from provided file paths."""
        models = []
        for ai_path in self.ai_file_paths:
            if ai_path and os.path.exists(ai_path):
                try:
                    models.append(tf.keras.models.load_model(ai_path))
                except Exception as e:
                    print(f"Failed to load AI model from {ai_path}: {e}")
                    models.append(None)
            else:
                models.append(None)
        return models

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
            continent_bonuses[cont] for cont, terrs in continents.items()
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
        self.territories = Territory.initialize_territories()
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
        self.territories = Territory.initialize_territories()
        for terr in self.territories.values():
            terr.set_owner(None)
            terr.troop_count = 0

    def generate_ai_input(self, player_id, phase, turn, troops_remaining=0):
        """
        Generates the AI input vector (448) for a given player and game phase.

        Args:
            player_id (int): The player for whom the input is generated.
            phase (str): The current phase ("deploy", "attack", or "fortify").
            troops_remaining (int): Troops left to deploy (default: 0).

        Returns:
            np.array: A 448-length input vector for the AI.
        """
        input_vector = []
        max_troops = 1  # Prevent division by zero, will update later
        troop_counts = []

        # ---- 1. Territory Ownership (One-Hot Encoding: 42*4 = 168) ----
        for territory in territories_with_adjacency:
            owner = self.territories[territory].owner
            one_hot = [1 if owner == p else 0 for p in range(1, 5)]
            input_vector.extend(one_hot)

        # ---- 2. Troop Counts (Raw: 42) ----
        for territory in territories_with_adjacency:
            troops = self.territories[territory].troop_count
            troop_counts.append(troops)
            input_vector.append(troops)
            max_troops = max(max_troops, troops)

        # ---- 3. Normalized Troop Counts (42) ----
        for troops in troop_counts:
            input_vector.append(troops / max_troops)

        # ---- 4. Surrounding Friendly Territory Count (42) ----
        for territory in territories_with_adjacency:
            owner = self.territories[territory].owner
            friendly_count = sum(
                1 for neighbor in territories_with_adjacency[territory]  # Correct lookup
                if self.territories[neighbor].owner == owner
            )
            input_vector.append(friendly_count)

        # ---- 5. Continent Ownership (One-Hot: 6*4 = 24) ----
        for continent, terr_list in continent_bonuses.items():
            for p in range(1, 5):
                owns_continent = all(self.territories[t].owner == p for t in terr_list)
                input_vector.append(1 if owns_continent else 0)

        # ---- 6. Continent Ownership Progress (6*4 = 24) ----
        for continent, terr_list in continent_bonuses.items():
            for p in range(1, 5):
                owned = sum(1 for t in terr_list if self.territories[t].owner == p)
                input_vector.append(owned / len(terr_list))

        # ---- 7. Current Troop Income (Raw: 4) ----
        troop_income = [self.calculate_troops(p) for p in range(1, 5)]
        input_vector.extend(troop_income)

        # ---- 8. Current Troop Income (Normalized: 4) ----
        max_income = max(troop_income) if max(troop_income) > 0 else 1
        input_vector.extend([t / max_income for t in troop_income])

        # ---- 9. Current Player (One-Hot Encoding: 4) ----
        input_vector.extend([1 if player_id == p else 0 for p in range(1, 5)])

        # ---- 10. Current Phase (One-Hot Encoding: 3) ----
        phase_dict = {"deploy": [1, 0, 0], "attack": [0, 1, 0], "fortify": [0, 0, 1]}
        input_vector.extend(phase_dict[phase])

        # ---- 11. Troops Remaining to Deploy (1) ----
        input_vector.append(troops_remaining)

        # ---- 12. Total Troops on Board Per Player (4) ----
        total_troops = [sum(t.troop_count for t in self.territories.values() if t.owner == p) for p in range(1, 5)]
        input_vector.extend(total_troops)

        # ---- 13. Turn Counter (1) ----
        input_vector.append(turn)

        # ---- 14. Cards Owned (One-Hot: 24) ----
        player_cards = self.cards.get_player_cards(player_id)
        owned_territories = set(card.territory for card in player_cards)

        for territory in territories_with_adjacency:
            input_vector.append(1 if territory in owned_territories else 0)

        # ---- 15. Previous Turn Input
        input_vector.extend(self.get_previous_input(player_id, phase))  # Will return 405 now

        return np.array(input_vector, dtype=np.float32)

    def get_previous_input(self, player_id, phase):
        """Fetches previous turn input vector if available; otherwise, returns zeros."""
        game_file = os.path.join(GAME_REPLAY_STORAGE, "current_game.json")
        if not os.path.exists(game_file):
            return [0] * 405  # No previous data

        with open(game_file, "r") as f:
            game_data = json.load(f)

        # Find the most recent turn where this player acted in the same phase
        for move in reversed(game_data["moves"]):
            if move["player"] == player_id and move["phase"] == phase:
                return move["state"][:405]

        return [0] * 405  # Default if no previous input exists


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

    def add_troops(self, troops):
        """Adds troops to the territory."""
        self.troop_count += troops

    def remove_troops(self, troops):
        """Removes troops from this territory.

        Args:
            troops (int): Number of troops to remove

        Returns:
            bool: True if successful, False if not enough troops
        """
        if self.troop_count >= troops:
            self.troop_count -= troops
            return True
        return False

    def set_troops(self, troops):
        """Sets the exact troop count (useful for battle outcomes)."""
        self.troop_count = max(0, troops)  # Ensure non-negative
        return self.troop_count

    @classmethod
    def initialize_territories(cls):
        new_dict = {}
        for name in territories_with_adjacency:
            new_t = Territory(name)
            new_dict[name] = new_t
        return new_dict

class Card:
    def __init__(self, territory, troop_type):
        self.territory = territory
        self.troop_type = troop_type  # "Infantry", "Cavalry", or "Artillery"
        self.owner = 0  # 0 = unassigned, 1–4 = player ID

    def assign_to(self, player_id):
        """Assigns this card to a player (1–4)."""
        if player_id in [1, 2, 3, 4]:
            self.owner = player_id

    def reset(self):
        """Returns the card to the unassigned pool."""
        self.owner = 0

    def is_unassigned(self):
        return self.owner == 0


class CardManager:
    def __init__(self):
        """Creates all cards using the territory_card_types from config."""
        self.cards = []

        for territory, troop_type in territory_card_types.items():
            self.cards.append(Card(territory, troop_type))

    def draw_card(self):
        """Randomly selects and assigns an unowned card. Returns the Card or None if none available."""
        unassigned = [card for card in self.cards if card.is_unassigned()]
        if not unassigned:
            return None
        return random.choice(unassigned)

    def assign_card(self, card, player_id):
        """Assigns a specific card object to a player."""
        if card and card.is_unassigned():
            card.assign_to(player_id)

    def play_cards(self, card_list):
        """
        Plays (returns to pool) a list of Card objects.
        Used when a player turns in cards.
        """
        for card in card_list:
            card.reset()

    def get_player_cards(self, player_id):
        """Returns a list of Card objects owned by the given player."""
        return [card for card in self.cards if card.owner == player_id]

    def get_all_cards(self):
        """Returns all card objects."""
        return self.cards

    def get_card_summary(self, player_id):
        """Returns a dictionary of {territory: troop_type} for the given player."""
        return {
            card.territory: card.troop_type
            for card in self.cards
            if card.owner == player_id
        }