import json
import socket
import time
from risk_game import RiskGame
from enviornment import Board


class RiskServer:
    def __init__(self, players, board, host="127.0.0.1", port=9999):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Buffer for incoming data from the socket
        self.buffer = ""

        try:
            self.server_socket.bind((host, port))
            self.server_socket.listen(1)
            print(f"✅ Server listening on {host}:{port}...")
        except OSError as e:
            print(f"❌ Failed to bind to {host}:{port}: {e}")
            raise

        print("⏳ Waiting for Godot client to connect...")
        self.conn, addr = self.server_socket.accept()
        print(f"✅ Godot connected from {addr}")

        self.board = board
        self.game = RiskGame(players, self.board)

    def get_next_command(self):
        """
        Receives data from the socket, buffers it, and returns one complete JSON command.
        Commands are separated by a newline character '\\n'.
        Handles socket timeouts gracefully and continues waiting.
        """
        # Search for a newline character, which marks the end of a command
        while "\n" not in self.buffer:
            try:
                # Receive data from the socket and append to the buffer
                data = self.conn.recv(1024)
                if not data:
                    # Connection closed by the client
                    print("❌ Godot client disconnected.")
                    return None
                self.buffer += data.decode("utf-8")
            except socket.timeout:
                # Socket timeout - this is expected due to the 1-second timeout
                # Continue waiting for data (don't return None unless actually disconnected)
                continue
            except ConnectionResetError:
                print("❌ Godot client connection was forcibly closed.")
                return None
            except Exception as e:
                print(f"❌ Error receiving data: {e}")
                return None

        # Split the buffer at the first newline to get one complete command
        command_str, self.buffer = self.buffer.split("\n", 1)

        try:
            # Clean the command string before parsing - remove ALL whitespace from start/end
            command_str = command_str.strip()

            # Parse the JSON string into a Python dictionary
            command = json.loads(command_str)
            print(f"📥 Received command: {command}")
            return command
        except json.JSONDecodeError:
            print(f"❌ Failed to decode JSON: '{command_str}'")
            return None

    def wait_for_command(self, command_type):
        """Waits for a specific command type from the client."""
        while True:
            cmd = self.get_next_command()
            if cmd is None:  # Handle disconnection
                return None
            if cmd.get("type") == command_type:
                return cmd
            # Handle other commands that might come in
            self.handle_command(cmd)

    def handle_command(self, command):
        """Handles incoming commands from Godot."""
        command_type = command.get("type")
        print(f"🔍 SERVER: Processing command type: {command_type}")

        if command_type == "request_troop_income":
            print("🔍 SERVER: Routing to troop income handler")
            self.handle_troop_income_request(command)
        elif command_type == "deploy_troops":
            print("🔍 SERVER: Routing to deploy troops handler")
            self.handle_deploy_troops(command)
        elif command_type == "request_player_cards":
            print("🔍 SERVER: Routing to player cards handler")
            self.handle_player_cards_request(command)
        else:
            print(f"❓ SERVER: Unknown command type: {command_type}")

    def handle_troop_income_request(self, command):
        """Handles request for troop income calculation."""
        player_id = command.get("player_id")
        print(f"🔍 SERVER: Handling troop income request for Player {player_id}")

        if player_id:
            troop_income = self.board.calculate_troops(player_id)
            print(f"💰 SERVER: Calculated {troop_income} troops for Player {player_id}")

            response = {
                "type": "troop_income_response",
                "player_id": player_id,
                "troop_income": troop_income
            }

            message = json.dumps(response) + "\n"
            self.conn.sendall(message.encode("utf-8"))
            print(f"📤 SERVER: Sent troop income response: Player {player_id} gets {troop_income} troops")
        else:
            print("❌ SERVER: No player_id in troop income request!")

    def handle_deploy_troops(self, command):
        """Handles troop deployment from Godot."""
        player_id = command.get("player_id")
        territory_name = command.get("territory")
        troop_count = command.get("troops")

        print(
            f"🔍 SERVER: Handling deploy troops - Player {player_id}, Territory: {territory_name}, Troops: {troop_count}")

        success = self.board.deploy_troops(player_id, territory_name, troop_count)
        print(f"✅ SERVER: Deploy result: {success}")

        response = {
            "type": "deploy_response",
            "success": success,
            "player_id": player_id,
            "territory": territory_name,
            "troops": troop_count
        }

        message = json.dumps(response) + "\n"
        self.conn.sendall(message.encode("utf-8"))
        print(f"📤 SERVER: Sent deploy response: {success} - Player {player_id}, {territory_name}, {troop_count} troops")

        # If successful, send updated board state
        if success:
            territory = self.board.get_territory(territory_name)
            if territory:
                print(f"🏰 SERVER: Sending territory update - {territory_name} now has {territory.troop_count} troops")
                self.send_territory_update(territory_name, territory.owner, territory.troop_count)
            else:
                print(f"❌ SERVER: Could not find territory {territory_name} after successful deploy!")

    def send_territory_update(self, territory_name, owner_id, troops=None):
        """Sends territory update including owner and troop count."""
        try:
            data = {
                "type": "territory_update",
                "name": territory_name,
                "owner": owner_id
            }

            # Include troops if provided
            if troops is not None:
                data["troops"] = troops

            message = json.dumps(data) + "\n"
            self.conn.sendall(message.encode("utf-8"))
            print(f"📤 Sent update: {territory_name} → owner {owner_id}, troops {troops}")
        except Exception as e:
            print(f"❌ Failed to send update: {e}")

    def send_phase_update(self, player_id, phase, is_user=True):
        """Sends phase update to client with user/AI indicator."""
        try:
            data = {
                "type": "phase_update",
                "player": player_id,
                "phase": phase,
                "is_user": is_user  # True for user turns, False for AI turns
            }
            message = json.dumps(data) + "\n"
            self.conn.sendall(message.encode("utf-8"))
            print(f"📤 Sent phase update: Player {player_id} - {phase} ({'User' if is_user else 'AI'})")
        except Exception as e:
            print(f"❌ Failed to send phase update: {e}")

    def send_turn_update(self, player_id):
        """Sends turn update to client."""
        try:
            data = {
                "type": "turn_update",
                "current_player": player_id
            }
            message = json.dumps(data) + "\n"
            self.conn.sendall(message.encode("utf-8"))
            print(f"📤 Sent turn update: Player {player_id}")
        except Exception as e:
            print(f"❌ Failed to send turn update: {e}")

    def send_full_board_state(self):
        """Sends the complete board state to Godot including troop counts."""
        print("📤 Sending full board state...")
        for name, territory in self.board.territories.items():
            self.send_territory_update(name, territory.owner, territory.troop_count)
        print("✅ Full board state sent")

    def handle_player_cards_request(self, command):
        """Handles request for current player's cards from Godot."""

        # Get current player from the game's internal state
        current_player_id = self.game.get_current_player()

        print(f"🃏 SERVER: Handling card request for current Player {current_player_id}")

        # Get player's cards from the card manager
        try:
            player_cards = self.board.cards.get_player_cards(current_player_id)

            # Convert Card objects to JSON-serializable format
            cards_data = []
            for card in player_cards:
                cards_data.append({
                    "name": card.territory,
                    "type": card.troop_type
                })

            print(f"🃏 SERVER: Found {len(cards_data)} cards for current Player {current_player_id}")
            for i, card in enumerate(cards_data):
                print(f"  Card {i + 1}: {card['name']} ({card['type']})")

            # Send response
            response = {
                "type": "player_cards_response",
                "player_id": current_player_id,
                "cards": cards_data
            }

            message = json.dumps(response) + "\n"
            self.conn.sendall(message.encode("utf-8"))
            print(f"📤 SERVER: Sent {len(cards_data)} cards for current Player {current_player_id}")

        except Exception as e:
            print(f"❌ SERVER: Error getting cards for current Player: {e}")

    def run_game(self):
        """
        Main game loop. Continuously processes incoming commands and updates game state.
        """
        # Send initial game state to client
        initial_player = self.game.get_current_player()
        initial_phase = self.game.get_current_phase()
        self.send_turn_update(initial_player)
        self.send_phase_update(initial_player, initial_phase, is_user=True)  # Assume first player is user

        print("🎮 Starting main game loop - waiting for commands...")

        # Main command processing loop
        while not self.game.game_over:
            # Get the next command from client
            command = self.get_next_command()

            if command is None:  # Client disconnected
                print("❌ Client disconnected, ending game")
                break

            command_type = command.get("type")
            print(f"📥 Processing command: {command_type}")

            # Handle the command based on its type
            if command_type == "end_phase":
                self.handle_end_phase(command)
            elif command_type == "request_troop_income":
                self.handle_troop_income_request(command)
            elif command_type == "deploy_troops":
                self.handle_deploy_troops(command)
            elif command_type == "request_current_player_cards":
                self.handle_player_cards_request(command)
            else:
                print(f"❓ Unknown command type: {command_type}")
                # Continue processing - don't break on unknown commands

        print("🏁 Game Over!")
        self.close()

    def handle_end_phase(self, command):
        """Handles end phase commands and advances the game state."""
        player = command.get("player")
        phase = command.get("phase")

        print(f"🏁 Player {player} ending {phase} phase")

        # --- Update Game State ---
        self.game.end_phase()

        # --- Send Updates to Godot ---
        new_player = self.game.get_current_player()
        new_phase = self.game.get_current_phase()
        new_is_user = self.game.players[new_player - 1] == "User"

        print(f"🔄 Game state updated: Player {new_player}, Phase {new_phase}, User: {new_is_user}")

        # Check if the turn changed
        if new_player != player:
            self.send_turn_update(new_player)
            print(f"📤 Sent turn update: Now Player {new_player}")

        # Always send phase update when phase ends
        self.send_phase_update(new_player, new_phase, is_user=new_is_user)
        print(f"📤 Sent phase update: Player {new_player} - {new_phase} ({'User' if new_is_user else 'AI'})")

        # If it's now an AI turn, simulate AI actions
        if not new_is_user:
            print("🤖 AI turn detected, simulating AI actions...")
            self.simulate_ai_turn(new_player, new_phase)

    def simulate_ai_turn(self, player_id, phase):
        """Simulates AI actions for the given player and phase."""
        import time

        print(f"🤖 Simulating AI Player {player_id} in {phase} phase")

        if phase == "deploy":
            # Simulate AI deployment
            print("🤖 AI thinking about deployments...")
            time.sleep(2)  # Simulate thinking time

            # For now, just end the phase immediately
            # Later this will be replaced with actual AI logic
            print("🤖 AI ending deploy phase")
            self.game.end_phase()

            # Send updates for the phase change
            new_player = self.game.get_current_player()
            new_phase = self.game.get_current_phase()
            new_is_user = self.game.players[new_player - 1] == "User"

            if new_player != player_id:
                self.send_turn_update(new_player)
            self.send_phase_update(new_player, new_phase, is_user=new_is_user)

            # If next player is also AI, continue simulation
            if not new_is_user:
                self.simulate_ai_turn(new_player, new_phase)

        elif phase == "attack":
            print("🤖 AI skipping attack phase")
            time.sleep(1)
            self.game.end_phase()

            # Send updates
            new_player = self.game.get_current_player()
            new_phase = self.game.get_current_phase()
            new_is_user = self.game.players[new_player - 1] == "User"

            if new_player != player_id:
                self.send_turn_update(new_player)
            self.send_phase_update(new_player, new_phase, is_user=new_is_user)

            if not new_is_user:
                self.simulate_ai_turn(new_player, new_phase)

        elif phase == "fortify":
            print("🤖 AI skipping fortify phase")
            time.sleep(1)
            self.game.end_phase()

            # Send updates
            new_player = self.game.get_current_player()
            new_phase = self.game.get_current_phase()
            new_is_user = self.game.players[new_player - 1] == "User"

            if new_player != player_id:
                self.send_turn_update(new_player)
            self.send_phase_update(new_player, new_phase, is_user=new_is_user)

            if not new_is_user:
                self.simulate_ai_turn(new_player, new_phase)

    def close(self):
        """Closes the server and client connections."""
        print("🔌 Closing connections...")
        self.conn.close()
        self.server_socket.close()
        print("✅ Connections closed.")


if __name__ == '__main__':
    # --- Example Usage ---
    players = ["User", "User"]  # Example: 2 human players
    board = Board()

    try:
        server = RiskServer(players, board)
        server.run_game()
    except Exception as e:
        print(f"An error occurred: {e}")