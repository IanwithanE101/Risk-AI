import time
from risk_game import RiskGame
from risk_server import RiskServer


class GameManager:
    def __init__(self, board, player_types, is_gui=False, gui=None):
        """
        Central controller for managing a Risk game session.

        Args:
            board (Board): The initialized board.
            player_types (list of str): ["User", "AI", "AI", "User"]
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
        """Starts the actual Risk game with proper turn management."""
        self.server = RiskServer(self.player_types, self.board)
        print("RiskServer initialized. Starting Risk game...")

        # Generate initial random board
        print("🎲 Generating initial random board...")
        self.board.generate_random_board()

        # Send initial board state to Godot
        self.server.send_full_board_state()
        print("📤 Initial board state sent to Godot")

        # Game state
        self.current_player = 1
        self.phases = ["deploy", "attack", "fortify"]

        # Main game loop
        while not self.check_game_over():
            print(f"\n=== Player {self.current_player}'s turn ===")

            # Determine if current player is user or AI
            player_type = self.player_types[self.current_player - 1]
            is_user = (player_type == "User")

            print(f"🎮 Player {self.current_player} is: {player_type}")

            # Notify Godot about the new turn
            self.server.send_turn_update(self.current_player)

            # Go through all phases for this player
            for phase in self.phases:
                print(f"📍 Phase: {phase} for Player {self.current_player} ({player_type})")

                # Send phase update with user/AI indicator
                self.server.send_phase_update(self.current_player, phase, is_user=is_user)

                if is_user:
                    # User turn - wait for Godot to handle the phase
                    print(f"⏳ Waiting for User Player {self.current_player} to complete {phase} phase...")
                    self.handle_user_phase(phase)
                else:
                    # AI turn - simulate AI actions
                    print(f"🤖 AI Player {self.current_player} executing {phase} phase...")
                    self.handle_ai_phase(phase)

                print(f"✅ Player {self.current_player} completed {phase} phase")

            # End of turn - move to next player
            self.current_player = (self.current_player % len(self.player_types)) + 1

        self.end_game()

    def handle_user_phase(self, phase):
        """Handles a user's phase by waiting for Godot input."""
        if phase == "deploy":
            # For deploy phase, we need to wait for all troops to be deployed
            # The end phase button will be disabled until all troops are used
            pass

        # Wait for player to end the phase
        cmd = self.server.wait_for_command("end_phase")

        if cmd is None:
            print("❌ Client disconnected during user phase")
            return False

        return True

    def handle_ai_phase(self, phase):
        """Handles an AI's phase with simulated actions."""
        # Simulate AI thinking time
        time.sleep(1)

        if phase == "deploy":
            self.simulate_ai_deploy()
        elif phase == "attack":
            self.simulate_ai_attack()
        elif phase == "fortify":
            self.simulate_ai_fortify()

        # AI automatically ends phase
        print(f"🤖 AI Player {self.current_player} automatically ended {phase} phase")

    def simulate_ai_deploy(self):
        """Simulates AI deploy actions."""
        print(f"🪖 AI Player {self.current_player} deploying troops...")

        # Get AI's territories
        ai_territories = [name for name, territory in self.board.territories.items()
                          if territory.owner == self.current_player]

        if ai_territories:
            # Calculate troops to deploy
            troops_to_deploy = self.board.calculate_troops(self.current_player)
            print(f"💰 AI gets {troops_to_deploy} troops to deploy")

            # Randomly distribute troops among AI's territories
            import random
            while troops_to_deploy > 0:
                territory_name = random.choice(ai_territories)
                deploy_amount = min(random.randint(1, 3), troops_to_deploy)

                # Deploy troops
                success = self.board.deploy_troops(self.current_player, territory_name, deploy_amount)
                if success:
                    troops_to_deploy -= deploy_amount
                    print(f"🎯 AI deployed {deploy_amount} troops to {territory_name}")

                    # Send update to Godot
                    territory = self.board.get_territory(territory_name)
                    self.server.send_territory_update(territory_name, territory.owner, territory.troop_count)

    def simulate_ai_attack(self):
        """Simulates AI attack actions."""
        print(f"⚔️ AI Player {self.current_player} considering attacks...")
        # For now, AI skips attack phase
        print("🤖 AI skips attack phase")

    def simulate_ai_fortify(self):
        """Simulates AI fortify actions."""
        print(f"🏰 AI Player {self.current_player} considering fortification...")
        # For now, AI skips fortify phase
        print("🤖 AI skips fortify phase")

    def check_game_over(self):
        """Checks if the game should end."""
        # Check for winner
        winner = self.board.check_winner()
        if winner:
            print(f"🏆 Player {winner} wins the game!")
            return True

        # For testing, limit to a certain number of rounds
        if self.current_turn > 20:  # Stop after 20 total turns
            print("🔄 Demo ended after 20 turns")
            return True

        return False

    def end_game(self):
        print("\n🎮 GAME OVER!")
        print("📊 Final board state:")
        self.print_final_stats()
        self.server.close()

    def print_final_stats(self):
        """Prints final game statistics."""
        player_stats = {1: {"territories": 0, "troops": 0},
                        2: {"territories": 0, "troops": 0},
                        3: {"territories": 0, "troops": 0},
                        4: {"territories": 0, "troops": 0}}

        for territory in self.board.territories.values():
            if territory.owner in player_stats:
                player_stats[territory.owner]["territories"] += 1
                player_stats[territory.owner]["troops"] += territory.troop_count

        for player_id in range(1, len(self.player_types) + 1):
            stats = player_stats[player_id]
            player_type = self.player_types[player_id - 1]
            print(
                f"   Player {player_id} ({player_type}): {stats['territories']} territories, {stats['troops']} troops")