import json
import os
from config import REWARD_CONFIG, GAME_REPLAY_STORAGE, SCORED_GAMES

class RiskScorer:
    """
    Scores stored game replays and saves scored versions for training.
    """

    def __init__(self, scoring_config=None):
        """
        Initializes the scorer with configurable reward values.

        Args:
            scoring_config (dict, optional): Custom reward values. Uses defaults if None.
        """
        self.reward_config = scoring_config if scoring_config else REWARD_CONFIG  # Use default if not provided

    def score_game(self, game_replay_file):
        """
        Loads a stored game replay, scores every move, and saves the scored version.

        Args:
            game_replay_file (str): The filename of the raw game replay.

        Returns:
            str: Path of the saved scored game file.
        """
        raw_game_path = os.path.join(GAME_REPLAY_STORAGE, game_replay_file)
        scored_game_path = os.path.join(SCORED_GAMES, game_replay_file)

        if not os.path.exists(raw_game_path):
            print(f"Game replay file not found: {raw_game_path}")
            return None

        with open(raw_game_path, "r") as f:
            game_data = json.load(f)  # List of (state, action, next_state)

        scored_data = []
        final_winner = game_data[-1]["winner"] if "winner" in game_data[-1] else None

        for move in game_data:
            player = move["player"]
            phase = move["phase"]
            prev_board = move["state"]
            new_board = move["next_state"]

            if phase == "deploy":
                reward = self.score_deploy(prev_board, new_board, player)
            elif phase == "attack":
                reward = self.score_attack(prev_board, new_board, player)
            elif phase == "fortify":
                reward = self.score_fortify(prev_board, new_board, player)
            else:
                reward = 0

            scored_data.append({
                "state": move["state"],
                "action": move["action"],
                "reward": reward,
                "next_state": move["next_state"],
                "done": move["done"],
                "player": player
            })

        # Apply endgame scaling
        for entry in scored_data:
            entry["reward"] = self.apply_endgame_scaling(entry["reward"], final_winner, entry["player"])

        # Save scored game
        os.makedirs(SCORED_GAMES, exist_ok=True)
        with open(scored_game_path, "w") as f:
            json.dump(scored_data, f, indent=4)

        print(f"Scored game saved: {scored_game_path}")
        return scored_game_path

    def score_deploy(self, prev_board, new_board, player):
        """Evaluates the Deploy phase based on troop placement."""
        reward = 0
        for name, terr in new_board["territories"].items():
            old_troops = prev_board["territories"][name]["troops"]
            new_troops = terr["troops"]

            if terr["owner"] == player and new_troops > old_troops:
                added_troops = new_troops - old_troops

                # Check if it's a border territory (has enemy neighbors)
                is_border = any(
                    new_board["territories"][n]["owner"] != player for n in terr["neighbors"]
                )

                if is_border:
                    reward += self.reward_config["DEPLOY_BORDER"] * added_troops
                    if new_troops == 2:
                        reward += self.reward_config["DEPLOY_2_BORDER"]

                else:
                    reward += self.reward_config["DEPLOY_SAFE"] * added_troops

                # Bonus for completing a continent
                if self.check_continent_completion(new_board, player, terr["continent"]):
                    reward += self.reward_config["DEPLOY_COMPLETE_CONTINENT"]

        return reward

    def score_attack(self, prev_board, new_board, player):
        """Evaluates the Attack phase based on territory captures and troop losses."""
        reward = 0
        captured_territories = 0
        total_troop_loss = 0

        for name, terr in new_board["territories"].items():
            old_territory = prev_board["territories"][name]

            if terr["owner"] == player and old_territory["owner"] != player:
                captured_territories += 1
                reward += self.reward_config["ATTACK_WIN_TERRITORY"]
                if terr["troops"] == 2:
                    reward += self.reward_config["ATTACK_LEAVE_2_BORDER"]

            if old_territory["owner"] == player and terr["owner"] != player:
                total_troop_loss += old_territory["troops"] - terr["troops"]

        if total_troop_loss > 5:
            reward += self.reward_config["ATTACK_HEAVY_LOSS"]

        if captured_territories == 0 and self.easy_attack_available(prev_board, player):
            reward += self.reward_config["ATTACK_SKIPPED"]

        if self.check_player_eliminated(prev_board, new_board):
            reward += self.reward_config["ATTACK_ELIMINATE_PLAYER"]

        if self.check_continent_completion(new_board, player):
            reward += self.reward_config["ATTACK_COMPLETE_CONTINENT"]

        return reward

    def score_fortify(self, prev_board, new_board, player):
        """Evaluates the Fortify phase based on troop movement."""
        reward = 0
        for name, terr in new_board["territories"].items():
            old_troops = prev_board["territories"][name]["troops"]
            new_troops = terr["troops"]

            if terr["owner"] == player:
                if new_troops > old_troops:
                    is_border = any(
                        new_board["territories"][n]["owner"] != player for n in terr["neighbors"]
                    )
                    if is_border:
                        reward += self.reward_config["FORTIFY_BORDER"] * (new_troops - old_troops)
                        if new_troops == 2:
                            reward += self.reward_config["FORTIFY_2_BORDER"]

                if old_troops > new_troops:
                    is_safe = all(
                        new_board["territories"][n]["owner"] == player for n in terr["neighbors"]
                    )
                    if is_safe:
                        reward += self.reward_config["FORTIFY_ABANDON_SAFE"]

        return reward

    def apply_endgame_scaling(self, total_rewards, winner, player):
        """Applies final scaling based on game outcome."""
        if player == winner:
            return total_rewards * self.reward_config["GAME_WIN_MULTIPLIER"]
        return total_rewards * self.reward_config["GAME_LOSE_MULTIPLIER"]

    def easy_attack_available(self, board, player):
        """Checks if an easy attack was available but skipped."""
        for terr in board["territories"].values():
            if terr["owner"] == player and terr["troops"] > 2:
                for neighbor in terr["neighbors"]:
                    if board["territories"][neighbor]["owner"] != player and board["territories"][neighbor]["troops"] < terr["troops"]:
                        return True
        return False

    def check_continent_completion(self, board, player, continent=None):
        """Checks if the player owns an entire continent."""
        if continent:
            return all(board["territories"][t]["owner"] == player for t in board["continents"][continent])
        return any(all(board["territories"][t]["owner"] == player for t in board["continents"][c]) for c in board["continents"])

    def check_player_eliminated(self, prev_board, new_board):
        """Checks if any player was eliminated in this turn."""
        prev_players = {t["owner"] for t in prev_board["territories"].values()}
        new_players = {t["owner"] for t in new_board["territories"].values()}
        return len(prev_players) > len(new_players)
