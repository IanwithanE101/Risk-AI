from risk_game import RiskGame


class GameManager:
    def __init__(self, board, player_types, is_gui=False, gui=None):
        """
        Central controller for managing a Risk game session.

        Args:
            board (Board): The initialized board.
            player_types (list of str): ["User", "AI", "AI", "User"]
            ai_models (list of models): List of 4 AI models or None for users.
            is_gui (bool): Whether this is a GUI-driven game.
            gui (RiskGameGUI): Optional reference to the GUI for visual overlays.
        """
        self.board = board
        self.player_types = player_types
        self.ai_models = board.get_ai_file_paths()
        self.is_gui = is_gui
        self.gui = gui
        self.risk_game = RiskGame(player_types, self.board)
        self.current_turn = 0
        self.replay_data = []  # for storing (state, action, next_state, reward/done)

    def start_game(self):
        # TODO: Begin main game loop
        pass

    def play_turn(self):
        # TODO: Execute all 3 phases for the current player
        pass

    def handle_deploy(self, player_id):
        # TODO: Deploy phase logic
        pass

    def handle_attack(self, player_id):
        # TODO: Attack phase logic
        pass

    def handle_fortify(self, player_id):
        # TODO: Fortify phase logic
        pass

    def get_ai_output(self, player_id, input_vector):
        # TODO: Run AI model with input vector
        pass

    def override_ai_output(self, ai_output, user_action):
        # TODO: Replace AI output with user-provided action
        pass

    def record_move(self, state, action, next_state, done):
        # TODO: Save replay step to replay_data or disk
        pass

    def check_game_over(self):
        # TODO: Return True if someone has won
        pass

    def end_game(self):
        # TODO: Save replay to GAME_REPLAY_STORAGE and exit loop
        pass
