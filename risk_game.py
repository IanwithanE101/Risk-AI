import random
from enviornment import Board


class RiskGame:
    """
    A fully independent Risk game logic class.
    - Manages game state (board, players, turns, and phases).
    - Allows both AI and GUI to interact with it.
    - Provides board access for AI training.
    """

    def __init__(self, players):
        """
        Initialize a new game.

        Args:
            players (list of str): List of player types, e.g. ["User", "AI", "AI", "User"].
        """
        self.board = Board(num_players=len(players))
        self.players = players
        self.current_player = 1
        self.phase = "deploy"
        self.troops_to_deploy = {p: self.calculate_initial_troops(p) for p in range(1, len(players) + 1)}
        self.game_over = False

    # ------------------------------
    # GAME STATE
    # ------------------------------
    def get_board_state(self):
        """Return the full board state for AI or GUI."""
        return self.board

    def get_current_player(self):
        """Return the current player number (1-4)."""
        return self.current_player

    def get_current_phase(self):
        """Return the current game phase."""
        return self.phase

    def calculate_initial_troops(self, player):
        """Calculate how many troops a player gets at the start of the game."""
        return max(3, len([t for t in self.board.territories.values() if t.owner == player]) // 3)

    def check_winner(self):
        """Checks if a single player controls the entire board."""
        owners = set(territory.owner for territory in self.board.territories.values() if territory.owner is not None)

        if len(owners) == 1:
            self.game_over = True
            return owners.pop()  # Return winning player ID
        return None

    def end_phase(self):
        """Move to the next phase or next player if needed."""
        phase_order = ["deploy", "attack", "fortify"]
        phase_index = phase_order.index(self.phase)

        if phase_index == len(phase_order) - 1:
            # End of fortify → Next player's deploy phase
            self.phase = "deploy"
            self.current_player += 1
            if self.current_player > len(self.players):
                self.current_player = 1
            self.troops_to_deploy[self.current_player] = self.calculate_initial_troops(self.current_player)
        else:
            # Move to the next phase
            self.phase = phase_order[phase_index + 1]

    # ------------------------------
    # DEPLOY PHASE
    # ------------------------------
    def deploy_troops(self, player, territory, count):
        """Deploy troops to a territory."""
        if self.phase != "deploy" or player != self.current_player:
            return False  # Invalid move

        if self.board.territories[territory].owner != player or count > self.troops_to_deploy[player]:
            return False  # Invalid deployment

        self.board.territories[territory].troop_count += count
        self.troops_to_deploy[player] -= count
        return True

    # ------------------------------
    # ATTACK PHASE
    # ------------------------------
    def roll_dice(self, num_dice):
        """Rolls dice and returns a sorted list (highest to lowest)."""
        return sorted([random.randint(1, 6) for _ in range(num_dice)], reverse=True)

    def blitz_attack(self, attacker, defender):
        """
        Executes a blitz attack until attacker wins or stops.

        Args:
            attacker (Territory): The attacking territory.
            defender (Territory): The defending territory.

        Returns:
            bool: True if attacker won, False otherwise.
        """
        while attacker.troop_count > 1 and defender.troop_count > 0:
            attacker_dice = min(3, attacker.troop_count - 1)
            defender_dice = min(2, defender.troop_count)

            attack_roll = self.roll_dice(attacker_dice)
            defense_roll = self.roll_dice(defender_dice)

            for a, d in zip(attack_roll, defense_roll):
                if a > d:
                    defender.troop_count -= 1
                else:
                    attacker.troop_count -= 1

        # If attacker wins and captures territory
        if defender.troop_count <= 0:
            defender.owner = attacker.owner  # Change ownership
            defender.troop_count = 1  # Default minimum troop count
            attacker.troop_count -= 1  # Move one troop automatically

            # **Check for victory immediately after capturing a territory**
            winner = self.check_winner()
            if winner:
                print(f"Game Over! Player {winner} wins.")
                self.game_over = True
                return True

        return False  # Attack did not result in victory

    def user_attack(self, attack_from, attack_to):
        """User selects an attack move."""
        if self.phase != "attack":
            return False  # Not attack phase

        attacker = self.board.territories[attack_from]
        defender = self.board.territories[attack_to]

        if not self.is_valid_attack(attacker, defender):
            return False  # Invalid attack

        if self.blitz_attack(attacker, defender):
            return attack_from, attack_to  # Returns for user to input troop move
        return None, None

    def user_post_attack_move(self, attack_from, attack_to, move_amount):
        """User moves troops after a successful attack."""
        if attack_from and attack_to:
            self.post_attack_movement(self.board.territories[attack_from], self.board.territories[attack_to],
                                      move_amount)

    def ai_attack(self, attack_from, attack_to, move_amount):
        """AI attacks and moves troops automatically."""
        if self.phase != "attack":
            return False

        attacker = self.board.territories[attack_from]
        defender = self.board.territories[attack_to]

        if not self.is_valid_attack(attacker, defender):
            return False

        if self.blitz_attack(attacker, defender):
            self.post_attack_movement(attacker, defender, move_amount)
        return True

    def post_attack_movement(self, attacker, defender, move_amount):
        """
        Moves troops after a successful attack.

        Args:
            attacker (Territory): The attacking territory.
            defender (Territory): The conquered territory.
            move_amount (int): Number of troops to move.
        """
        move_amount = max(1, min(move_amount, attacker.troop_count - 1))
        defender.owner = attacker.owner
        defender.troop_count = move_amount
        attacker.troop_count -= move_amount

    # ------------------------------
    # FORTIFY PHASE
    # ------------------------------
    def user_fortify(self, from_territory, to_territory):
        """User selects a fortify move."""
        if self.phase != "fortify":
            return False  # Not fortify phase

        if not self.is_valid_fortify(from_territory, to_territory):
            return False

        return from_territory, to_territory  # Return to let user pick troops

    def user_fortify_amount(self, from_territory, to_territory, move_amount):
        """User moves troops after selecting fortify move."""
        if from_territory and to_territory:
            self.fortify_troops(self.board.territories[from_territory], self.board.territories[to_territory],
                                move_amount)

    def ai_fortify(self, from_territory, to_territory, move_amount):
        """AI executes a fortify move automatically."""
        if self.phase != "fortify":
            return False

        if not self.is_valid_fortify(from_territory, to_territory):
            return False

        self.fortify_troops(self.board.territories[from_territory], self.board.territories[to_territory], move_amount)
        return True

    def fortify_troops(self, from_territory, to_territory, move_amount):
        """Executes troop movement for fortification."""
        move_amount = max(1, min(move_amount, from_territory.troop_count - 1))
        from_territory.troop_count -= move_amount
        to_territory.troop_count += move_amount

    # ------------------------------
    # VALIDATION HELPERS
    # ------------------------------
    def is_valid_attack(self, attacker, defender):
        """Checks if the attack move is valid."""
        return (
                attacker.owner == self.current_player and
                defender.owner != self.current_player and
                defender.name in attacker.adjacent_territories and
                attacker.troop_count > 1
        )

    def is_valid_fortify(self, from_territory, to_territory):
        """Checks if the fortify move is valid."""
        return (
                self.board.territories[from_territory].owner == self.current_player and
                self.board.territories[to_territory].owner == self.current_player
        )
