import datetime
import os
import pickle

from config import GAME_REPLAY_STORAGE

class GameReplayStorage:
    """
    Stores full game replays by saving every move (state, action, next_state).
    Each game creates a new file based on the current date and time.
    """

    def __init__(self):
        self.moves = []  # Stores (state, action, next_state, done)
        os.makedirs(GAME_REPLAY_STORAGE, exist_ok=True)  # Ensure directory exists

    def store(self, state, action, next_state, done):
        """
        Stores a single move in the replay storage.
        Args:
            state (np.array): The game state before the action.
            action (np.array): The AI or player action taken.
            next_state (np.array): The resulting game state after the move.
            done (bool): Whether the game ended after this move.
        """
        self.moves.append((state, action, next_state, done))

    def save_game(self):
        """
        Saves the full game replay as a new file with a timestamped filename.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(GAME_REPLAY_STORAGE, f"game_replay_{timestamp}.pkl")

        with open(filename, "wb") as f:
            pickle.dump(self.moves, f)

        print(f"Game replay saved: {filename}")

    def load_game(self, filename):
        """
        Loads a previously saved game replay.
        Args:
            filename (str): The name of the file to load.
        Returns:
            list: The stored moves from the game.
        """
        filepath = os.path.join(GAME_REPLAY_STORAGE, filename)
        if not os.path.exists(filepath):
            print(f"Replay file not found: {filepath}")
            return None

        with open(filepath, "rb") as f:
            return pickle.load(f)
