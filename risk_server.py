import socket
import json
from enviornment import Board
from risk_game import RiskGame

class RiskServer:
    class RiskServer:
        def __init__(self, players, board, host="localhost", port=9999):
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((host, port))
            self.server_socket.listen(1)
            print(f"Listening for Godot on {host}:{port}...")
            self.conn, _ = self.server_socket.accept()
            print("Godot connected.")

            self.board = board  # ✅ Use the existing board object
            self.game = RiskGame(players, self.board)

    # 1. Converts the current board to JSON
    def get_board_state_json(self):
        state = {}
        for name, territory in self.board.territories.items():
            state[name] = {
                "owner": territory.owner,
                "troops": territory.troop_count
            }
        return json.dumps({"type": "board", "data": state})

    # 2. Sends the current board to Godot
    def send_board_state(self):
        json_data = self.get_board_state_json()
        self.conn.sendall((json_data + "\n").encode("utf-8"))
