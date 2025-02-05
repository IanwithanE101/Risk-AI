from Enviornment import boardmanagement, Player, AiFunctions

class Train:
    # === Configuration Variables ===
    num_players = 16      # Number of independent AI players being trained
    num_games = 300        # Total number of games to train each player
    starting_troops = 30   # Initial deployment troops
    turn_limit = 1000      # Maximum turns per game
    epsilon = 0.99         # Exploration-exploitation parameter
    epsilon_min = 0.5      # Minimum value for epsilon
    epsilon_decay = 0.9    # Decay factor for epsilon after each game

    @staticmethod
    def train_player(player):
        """Train a single AI bot by having it play against itself."""
        print(f"\nTraining started for AI Player {player.player_id}.\n")

        epsilon = Train.epsilon  # Use the class-level epsilon variable
        game_count = 0

        while game_count < Train.num_games:
            # Generate a new game board using boardmanagement class
            territory_data = boardmanagement.generate_new_board()

            # Initial Deployment Phase
            for turn in range(1, 5):  # Fixed to 4 players in a single game
                AiFunctions.deploy_AI(
                    player_num=player.player_id,
                    player_num_relative=turn,
                    territory_data=territory_data,
                    epsilon=epsilon,
                    override_troops=Train.starting_troops
                )

            round_num = 0
            while round_num < Train.turn_limit:
                winner = boardmanagement.check_winner(territory_data)
                if winner is not None:
                    print(f"Game completed for AI Player {player.player_id}. Winner: Player {winner}")
                    break

                # Each player (1–4) takes their turn
                for player_num in range(1, 5):  # Fixed to 4 players
                    # Ensure the current player has territories
                    alive_territories = [
                        t for t, data in territory_data.items() if data["owner"] == player_num
                    ]
                    if not alive_territories:
                        continue

                    # Execute AI-controlled actions for the current player
                    AiFunctions.deploy_AI(player.player_id, player_num, territory_data, epsilon)
                    AiFunctions.attack_AI(player.player_id, player_num, territory_data, epsilon)
                    AiFunctions.fortify_AI(player.player_id, player_num, territory_data, epsilon)

                round_num += 1

            # Decay epsilon
            epsilon = max(Train.epsilon_min, epsilon * Train.epsilon_decay)
            game_count += 1

            print(f"Game {game_count} completed for AI Player {player.player_id}.\n")

    @staticmethod
    def start_training():
        """Start training by initializing players and executing training for each."""
        # Initialize all players in the Players array
        Players = [Player(player_id) for player_id in range(0, Train.num_players)]

        # Train each player sequentially
        for player in Players:
            Train.train_player(player)

    @staticmethod
    def display_training_params():
        """Display current training parameters and confirm to proceed."""
        print("Training Parameters:")
        print(f"Number of Players: {Train.num_players}")
        print(f"Number of Games: {Train.num_games}")
        print(f"Starting Troops: {Train.starting_troops}")
        print(f"Turn Limit: {Train.turn_limit}")
        print(f"Initial Epsilon: {Train.epsilon}")
        print(f"Minimum Epsilon: {Train.epsilon_min}")
        print(f"Epsilon Decay: {Train.epsilon_decay}")

        confirmation = input("Do you want to proceed with these settings? (y/n): ")
        if confirmation.lower() != 'y':
            print("Training aborted.")
            return False

        return True

if __name__ == "__main__":
    if Train.display_training_params():
        Train.start_training()
