import os
import pygame
import json
from PIL import Image
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BACKGROUND_IMAGE_PATH, TERRITORY_MAP_PATH, FONT_PATH
from enviornment import Board

class RiskGameGUI:
    """
    The Pygame-based interface for playing the Risk game.
    """

    def __init__(self, board, player_types):
        """
        Initializes the game UI with a given board and player settings.

        Args:
            board (Board): The game board object.
            player_types (list): A list of 4 strings ["User", "AI", "User", "AI"]
        """
        self.board = board  # Store the board object
        self.player_types = player_types  # Store player types
        self.window_width = SCREEN_WIDTH
        self.window_height = SCREEN_HEIGHT
        self.board_height = int(0.95 * self.window_height)  # 90% of screen height
        self.control_height = self.window_height - self.board_height  # Remaining 10% for controls
        self.running = True

        pygame.init()
        pygame.display.set_caption("Risk Game")

        # Setup display
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)

        # Set window icon
        self.set_window_icon()

        # Load assets
        self.background_image = self.load_background()
        self.territory_positions = self.load_territory_positions()
        self.displayed_territories = self.load_territory_images()


    def set_window_icon(self):
        """Loads and sets the window icon."""
        try:
            if os.path.exists(BACKGROUND_IMAGE_PATH):
                icon = pygame.image.load(BACKGROUND_IMAGE_PATH).convert_alpha()
                icon = pygame.transform.scale(icon, (32, 32))
                pygame.display.set_icon(icon)
        except Exception as e:
            print(f"Failed to set window icon: {e}")

    def load_background(self):
        """Loads and scales the game board background."""
        if os.path.exists(BACKGROUND_IMAGE_PATH):
            bg = pygame.image.load(BACKGROUND_IMAGE_PATH).convert_alpha()
            return pygame.transform.scale(bg, (self.window_width, self.board_height))  # Scale only to board height
        else:
            surface = pygame.Surface((self.window_width, self.board_height))
            surface.fill((200, 200, 200))  # Default grey background
            return surface

    def load_territory_positions(self):
        """Loads troop position data from JSON."""
        if not os.path.exists(TERRITORY_MAP_PATH):
            print(f"Error: {TERRITORY_MAP_PATH} not found.")
            return {}

        with open(TERRITORY_MAP_PATH, "r") as f:
            return json.load(f)

    def load_territory_images(self):
        """
        Loads and scales all territory images based on the board's defined territories.
        Also recolors each image to match ownership.
        """
        territories = {}
        for name, territory in self.board.territories.items():
            path = territory.get_image_path()
            if os.path.exists(path):
                try:
                    orig_img = Image.open(path).convert("RGBA")

                    # Recolor the image
                    recolored_img = self.recolor_territory_image(orig_img, territory.get_owner())

                    # Convert to Pygame surface
                    pygame_img = pygame.image.fromstring(recolored_img.tobytes(), recolored_img.size, "RGBA")
                    scaled_img = pygame.transform.scale(pygame_img, (self.window_width, self.board_height))
                    rect = scaled_img.get_rect(topleft=(0, 0))

                    territories[name] = {"image": scaled_img, "rect": rect}
                except Exception as e:
                    print(f"Could not load territory {name} from {path}: {e}")

        return territories

    def recolor_territory_image(self, img, owner_id):
        """Recolors **every single** white pixel in a territory image."""
        color_map = {
            1: (200, 30, 30),   # Player 1: Duller Red
            2: (30, 200, 30),   # Player 2: Duller Green
            3: (30, 30, 200),   # Player 3: Duller Blue
            4: (200, 200, 30),  # Player 4: Duller Yellow
            None: (250, 250, 250)  # Unowned: Light Gray
        }
        target_color = color_map.get(owner_id, (250, 250, 250))

        # Define a threshold for "almost white"
        threshold = 150  # Any color where R, G, and B are >150 is considered "white-like"

        img = img.convert("RGBA")
        pixels = img.load()

        width, height = img.size
        for x in range(width):
            for y in range(height):
                r, g, b, a = pixels[x, y]
                if a > 0 and r > threshold and g > threshold and b > threshold:
                    # If pixel is close to white, recolor it
                    pixels[x, y] = (*target_color, a)  # Preserve original alpha

        return img

    def draw_board(self):
        """Draws the game board in steps."""
        self.screen.blit(self.background_image, (0, 0))  # Draw board at the top

        # Step 1: Draw territories
        self.draw_territories()

        # Step 2: Draw troop counts
        self.draw_territory_troop_counts()

        # Step 3: Draw control panel at bottom
        self.draw_control_panel()

        pygame.display.flip()

    def draw_territories(self):
        """Blits each territory onto the screen with proper recoloring."""
        for territory_data in self.displayed_territories.values():
            self.screen.blit(territory_data["image"], territory_data["rect"])

    def draw_territory_troop_counts(self):
        """Draws troop counts on each territory using positions from JSON."""
        if not self.territory_positions:
            return

        font = pygame.font.Font(FONT_PATH, 30)

        # Scale troop number positions from 512x288 to actual window size
        ratio_x = self.window_width / 512.0
        ratio_y = self.board_height / 288.0

        for name, territory in self.board.territories.items():
            if name not in self.territory_positions:
                continue

            # Get troop count position
            pos_data = self.territory_positions[name]
            draw_x = int(pos_data["x"] * ratio_x)
            draw_y = int(pos_data["y"] * ratio_y)

            # Render troop count text
            text_surface = font.render(str(territory.troop_count), True, (0, 0, 0))
            text_rect = text_surface.get_rect(center=(draw_x, draw_y))

            self.screen.blit(text_surface, text_rect)

    def draw_game_over_screen(self, winner):
        """Displays a game over screen with the winning player number."""
        overlay = pygame.Surface((self.window_width, self.board_height))  # Limit overlay to board height
        overlay.set_alpha(200)  # Semi-transparent overlay
        overlay.fill((0, 0, 0))  # Dark overlay
        self.screen.blit(overlay, (0, 0))

        font = pygame.font.Font(FONT_PATH, 80)
        text = font.render(f"Player {winner} Wins!", True, (255, 255, 255))
        text_rect = text.get_rect(center=(self.window_width // 2, self.board_height // 2))  # Center in board area

        self.screen.blit(text, text_rect)
        pygame.display.flip()

    def draw_control_panel(self):
        """Draws the dark grey control panel at the bottom 10% of the screen."""
        panel_rect = pygame.Rect(0, self.board_height, self.window_width, self.control_height)
        pygame.draw.rect(self.screen, (50, 50, 50), panel_rect)  # Dark grey fill

    def run(self):
        """Main game loop."""
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.window_width, self.window_height = event.w, event.h
                    self.background_image = self.load_background()
                    self.displayed_territories = self.load_territory_images()

            self.draw_board()

            # **Check for victory condition**
            winner = self.board.check_winner()
            if winner is not None:
                self.draw_game_over_screen(winner)
                pygame.time.delay(5000)  # Display for 5 seconds
                self.running = False  # Exit game loop

        pygame.quit()
