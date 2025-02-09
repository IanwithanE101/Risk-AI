# Import libraries
import random
import multiprocessing
import numpy as np
from PIL import Image, ImageDraw, ImageTk
import json
import logging
import random
import time
import plotly.io as pio
import matplotlib.pyplot as plt
import pickle

# Define constants
NUM_TERRITORIES = 42  # Total number of territories
NUM_PLAYERS = 4       # Total number of players

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

class boardmanagement:
    def generate_new_board(territories=None, num_players=NUM_PLAYERS):
        if territories is None:
            territories = list(territories_with_adjacency.keys())

        random.shuffle(territories)

        territory_data = {}
        for i, territory in enumerate(territories):
            owner = (i % num_players) + 1
            territory_data[territory] = {"owner": owner, "troops": 1}

        return territory_data

    def calculate_troops(player_id, territory_data):
        global continents, continent_bonuses

        territories_owned = sum(1 for t in territory_data.values() if t["owner"] == player_id)

        territory_bonus = max(territories_owned // 3, 3)

        continent_bonus = 0
        for continent, territories in continents.items():
            if all(territory_data[t]["owner"] == player_id for t in territories):
                continent_bonus += continent_bonuses[continent]

        return territory_bonus + continent_bonus

    def find_connected_territories(player_id, source, territory_data):
        global territories_with_adjacency

        visited = set()
        stack = [source]
        connected = []

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)

            if current != source and territory_data[current]["owner"] == player_id:
                connected.append(current)

            neighbors = territories_with_adjacency[current]
            for neighbor in neighbors:
                if neighbor not in visited and territory_data[neighbor]["owner"] == player_id:
                    stack.append(neighbor)

        return connected

    def check_winner(board_state):
        if not board_state:
            return None

        owners = {data["owner"] for data in board_state.values() if "owner" in data}

        return owners.pop() if len(owners) == 1 else None

class Player:
    def __init__(self, player_id, p1=None, p2=None):
        self.player_id = player_id
        self.q_tables = {
            'deploy': {},
            'attack_from': {},
            'attack_target': {},
            'attack_decision': {},
            'fortify_from': {},
            'fortify_to': {},
            'fortify_decision': {},
            'fortify_transfer': {}
        }

        self.rewards = {
            'valid_deploy': random.uniform(1, 3),
            'deploy_edge': random.uniform(3, 10),
            'attack_decision': random.uniform(1, 5),
            'attack_from': random.uniform(3, 15),
            'attack_target': random.uniform(3, 10),
            'attack_success': random.uniform(5, 25),
            'attack_failure': random.uniform(-1, -5),
            'attack_advantage': random.uniform(2, 10),
            'fortify_decision': random.uniform(1, 5),
            'fortify_from': random.uniform(3, 10),
            'fortify_to': random.uniform(3, 10),
            'fortify_largest_troop': random.uniform(3, 10),
            'fortify_adjacent_opponent': random.uniform(3, 10),
            'troop_transfer': random.uniform(1, 5),
        }

        self.penalties = {
            'invalid_action': random.uniform(-0.5, -2),
        }

        if p1 and p2:
            for category in self.q_tables:
                parent = random.choice([p1, p2])
                self.q_tables[category] = parent.q_tables[category].copy()
        if p1:
            for category in self.q_tables:
                self.q_tables[category] = p1.q_tables[category].copy()

    def get_reward(self, key):
        return self.rewards.get(key, 0)

    def get_penalty(self, key):
        return self.penalties.get(key, 0)

    def get_q_values(self, phase, state_data):
        q_table = self.q_tables[phase]
        if state_data not in q_table:
            q_table[state_data] = [0] * len(territories_with_adjacency)
        return q_table[state_data]

    def update_qtable(self, phase, state_data, action_index, reward, learning_rate=0.4, discount_factor=0.9):
        q_table = self.q_tables[phase]
        if state_data not in q_table:
            q_table[state_data] = [0] * len(territories_with_adjacency)

        current_q_value = q_table[state_data][action_index]
        best_future_q_value = max(q_table[state_data])
        updated_q_value = (1 - learning_rate) * current_q_value + learning_rate * (reward + discount_factor * best_future_q_value)
        q_table[state_data][action_index] = updated_q_value

class AiFunctions:
    @staticmethod
    def prepare_ai_input(territory_data, current_player):
        # Keep the existing implementation
        continent_ownership = []
        for continent, territories in continents.items():
            owners = [territory_data[territory]['owner'] for territory in territories]
            if all(owner == owners[0] for owner in owners):
                continent_owner = owners[0]
            else:
                continent_owner = -1

            continent_one_hot = [0, 0, 0, 0]
            if continent_owner != -1:
                continent_one_hot[continent_owner - 1] = 1
            continent_ownership.extend(continent_one_hot)

        ownership = []
        for territory in territory_data.values():
            owner_one_hot = [0, 0, 0, 0]
            owner_one_hot[territory['owner'] - 1] = 1
            ownership.extend(owner_one_hot)

        troop_counts = [territory['troops'] for territory in territory_data.values()]
        max_troops = max(troop_counts) if troop_counts else 1
        normalized_troops = [territory['troops'] / max_troops for territory in territory_data.values()]

        current_player_one_hot = [0, 0, 0, 0]
        current_player_one_hot[current_player - 1] = 1

        input_vector = np.array(
            ownership + normalized_troops + continent_ownership + current_player_one_hot
        )

        return input_vector

    @staticmethod
    def deploy_AI(player_num, player_num_relative, territory_data, epsilon, override_troops=None):
        if override_troops is not None:
            troops_to_deploy = override_troops
        else:
            troops_to_deploy = boardmanagement.calculate_troops(player_num_relative, territory_data)

        retry_limit = 1000
        retry_count = 0

        while troops_to_deploy > 0:
            retry_count += 1
            if retry_count > retry_limit:
                break

            # Call prepare_ai_input properly as part of AiFunctions
            state_vector = AiFunctions.prepare_ai_input(territory_data, player_num_relative)
            state_hash = hash(tuple(state_vector))
            q_values_deploy = Players[player_num].get_q_values('deploy', state_hash)

            if random.random() < epsilon:
                deploy_index = random.randint(0, len(territory_data) - 1)
            else:
                deploy_index = np.argmax(q_values_deploy)

            deploy_territory = list(territory_data.keys())[deploy_index]

            if territory_data[deploy_territory]["owner"] != player_num_relative:
                penalty = Players[player_num].get_penalty('invalid_action')
                Players[player_num].update_qtable('deploy', state_hash, deploy_index, penalty)
                continue

            base_reward = Players[player_num].get_reward('valid_deploy')
            edge_reward = Players[player_num].get_reward('deploy_edge')
            opponent_adjacent_count = sum(
                1 for adj in territories_with_adjacency[deploy_territory] if territory_data[adj]["owner"] != player_num
            )
            if territories_with_adjacency[deploy_territory]:
                edge_deploy_reward = edge_reward * (
                    opponent_adjacent_count / len(territories_with_adjacency[deploy_territory])
                )
            else:
                edge_deploy_reward = 0

            reward = base_reward + edge_deploy_reward
            Players[player_num].update_qtable('deploy', state_hash, deploy_index, reward)

            territory_data[deploy_territory]["troops"] += 1
            troops_to_deploy -= 1

        return
