import os
import pygame
import json
from PIL import Image
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BACKGROUND_IMAGE_PATH, TERRITORY_MAP_PATH, FONT_PATH, GUI_ELEMENTS_PATH
from enviornment import Board
from game_manager import GameManager

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
        self.current_overlay = None
        self.hover_active = True
        self.hover_mode = "deploy"

        pygame.init()
        pygame.display.set_caption("Risk Game")
        self.clock = pygame.time.Clock()

        # Setup display
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)

        # Set window icon
        self.set_window_icon()

        # Load assets
        self.background_image = self.load_background()
        self.territory_positions = self.load_territory_positions()
        self.displayed_territories = self.load_territory_images()
        # Load original (unscaled) images
        self.original_close_icon = self.load_image("X.png")
        self.original_settings_icon = self.load_image("Gear.png")

        self.scale_ui_elements()

        self.game_manager = GameManager(board=self.board, player_types=self.player_types, is_gui=True, gui=self)


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
        """Draws the dark grey control panel at the bottom 10% of the screen, including the settings button."""

        # Draw the control panel background
        panel_rect = pygame.Rect(0, self.board_height, self.window_width, self.control_height)
        pygame.draw.rect(self.screen, (50, 50, 50), panel_rect)  # Dark grey fill

        # Load and resize settings button image (80% height of control panel, square aspect ratio)
        button_size = int(self.control_height * 0.8)  # 80% of panel height
        self.settings_button_img = self.load_and_resize_image("Gear.png", button_size, button_size)

        # Calculate settings button position (Far right, centered vertically)
        button_x = self.window_width - button_size - 10  # 10px padding from right
        button_y = self.board_height + (self.control_height - button_size) // 2

        # Store button rect for click detection
        self.settings_button_rect = pygame.Rect(button_x, button_y, button_size, button_size)

        # Draw the settings button
        if self.settings_button_img:
            self.screen.blit(self.settings_button_img, (button_x, button_y))
        else:
            # If image loading fails, draw a placeholder button (bright lime green)
            pygame.draw.rect(self.screen, (0, 255, 0), self.settings_button_rect)

    def load_and_resize_image(self, filename, width, height):
        """Loads an image from the GUI_ELEMENTS folder and resizes it.
           If the file is missing, return a bright lime green placeholder."""
        path = os.path.join(GUI_ELEMENTS_PATH, filename)

        if os.path.exists(path):
            img = pygame.image.load(path)
            return pygame.transform.scale(img, (width, height))

        # Create a bright lime green placeholder image
        placeholder = pygame.Surface((width, height))
        placeholder.fill((0, 255, 0))  # RGB for lime green
        return placeholder

    def update_control_panel(self, phase):
        """Updates the control panel display based on the current phase."""
        # Draw background panel
        panel_rect = pygame.Rect(0, self.board_height, self.window_width, self.control_height)
        pygame.draw.rect(self.screen, (50, 50, 50), panel_rect)

        # Draw the phase text centered
        font = pygame.font.Font(FONT_PATH, int(self.control_height * 0.5))
        text_surface = font.render(phase.upper(), True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self.window_width // 2, self.board_height + self.control_height // 2))
        self.screen.blit(text_surface, text_rect)

        # Draw the "End [PHASE]" button near the settings button
        button_height = int(self.control_height * 0.6)
        button_width = int(self.window_width * 0.12)
        button_x = self.window_width - button_width - self.settings_button_rect.width - 20
        button_y = self.board_height + (self.control_height - button_height) // 2

        self.end_phase_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

        pygame.draw.rect(self.screen, (100, 100, 100), self.end_phase_button_rect)  # Grey button background
        pygame.draw.rect(self.screen, (200, 200, 200), self.end_phase_button_rect, 2)  # Light border

        end_text = font.render(f"End {phase.title()}", True, (255, 255, 255))
        end_text_rect = end_text.get_rect(center=self.end_phase_button_rect.center)
        self.screen.blit(end_text, end_text_rect)

        # Redraw the settings button over top
        if self.settings_button_img:
            self.screen.blit(self.settings_button_img, self.settings_button_rect.topleft)

    def close_overlay(self):
        """Closes any active overlay."""
        self.current_overlay = None
        self.draw_board()  # Refresh the game board

    def animate_ai_turn(self, actions):
        """Animates AI moves so the user sees what happens."""
        self.hover_active = False

    def show_settings_menu(self):
        """Displays a scalable settings menu overlay with a properly scaled close button at the top-right."""

        # Draw the overlay visuals once initially
        overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))

        # Settings menu dimensions (50% width, 50% height of the screen)
        box_width = int(self.window_width * 0.5)
        box_height = int(self.window_height * 0.5)

        settings_box = pygame.Surface((box_width, box_height))
        settings_box.fill((180, 180, 180))
        box_rect = settings_box.get_rect(center=(self.window_width // 2, self.window_height // 2))

        # Close button (8% of settings box height)
        close_button_size = int(box_height * 0.08)
        padding = int(close_button_size * 0.3)
        close_button_x = box_rect.right - close_button_size - padding
        close_button_y = box_rect.top + padding
        self.close_button_rect = pygame.Rect(close_button_x, close_button_y, close_button_size, close_button_size)

        # Draw visuals
        self.screen.blit(overlay, (0, 0))
        self.screen.blit(settings_box, box_rect.topleft)
        if self.original_close_icon:
            resized_close_icon = pygame.transform.scale(self.original_close_icon,
                                                        (close_button_size, close_button_size))
            self.screen.blit(resized_close_icon, (close_button_x, close_button_y))
        else:
            pygame.draw.rect(self.screen, (255, 0, 0), self.close_button_rect)
        pygame.display.flip()

        # Wait for events passively (no need to redraw continuously)
        while self.current_overlay == "settings":
            event = pygame.event.wait()  # Pauses execution here until any input is received
            self.handle_event(event)

    def handle_event(self, event):
        """Handles UI events like clicking settings or closing overlays."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos

            # Open settings menu only if no other overlay is active
            if self.current_overlay is None and hasattr(self,'settings_button_rect') and self.settings_button_rect.collidepoint(x, y):
                self.current_overlay = "settings"
                self.draw_overlay()

            # Close settings menu (X button)
            elif self.current_overlay == "settings" and hasattr(self,'close_button_rect') and self.close_button_rect.collidepoint(x, y):
                self.current_overlay = None
                self.draw_board()  # immediately redraw main board
        elif event.type == pygame.MOUSEMOTION and self.hover_active:
            mouse_x, mouse_y = event.pos
            for name, territory_data in self.displayed_territories.items():
                if territory_data["rect"].collidepoint(mouse_x, mouse_y):
                    print(f"[{self.hover_mode.upper()} HOVER] Over territory: {name}")
                    break

    def load_image(self, filename):
        """Loads an image from GUI_ELEMENTS_PATH or returns a placeholder if missing."""
        path = os.path.join(GUI_ELEMENTS_PATH, filename)
        if os.path.exists(path):
            return pygame.image.load(path).convert_alpha()

        # Placeholder (lime green)
        placeholder = pygame.Surface((50, 50), pygame.SRCALPHA)
        placeholder.fill((0, 255, 0))
        return placeholder

    def scale_ui_elements(self):
        """Scales UI elements according to the current window/control dimensions."""

        # Settings button (Gear.png) scaled based on control panel height
        button_size = int(self.control_height * 0.8)
        if self.original_settings_icon:
            self.settings_button_img = pygame.transform.scale(
                self.original_settings_icon, (button_size, button_size)
            )
        else:
            self.settings_button_img = pygame.Surface((button_size, button_size))
            self.settings_button_img.fill((0, 255, 0))

        # Close button scaled proportionally based on settings menu size
        settings_box_width = int(self.window_width * 0.4)
        settings_box_height = int(self.window_height * 0.4)
        close_button_size = int(settings_box_height * 0.1)

        if self.original_close_icon:
            self.close_icon = pygame.transform.scale(
                self.original_close_icon, (close_button_size, close_button_size)
            )
        else:
            self.close_icon = pygame.Surface((close_button_size, close_button_size))
            self.close_icon.fill((255, 0, 0))

    def draw_overlay(self):
        """Centralized method for drawing active overlays based on current_overlay."""
        if self.current_overlay == "settings":
            self.show_settings_menu()
        # You can add more overlays here as elif cases in the future

    def run(self):
        """Main game loop."""
        while self.running:
            self.clock.tick(60)  # Limit FPS to 60

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False


                elif event.type == pygame.VIDEORESIZE:
                    # Update the window dimensions
                    self.window_width, self.window_height = event.w, event.h
                    # Recalculate vertical dimensions explicitly
                    self.board_height = int(0.95 * self.window_height)
                    self.control_height = self.window_height - self.board_height

                    # Resize the pygame window
                    self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)

                    # Reload and rescale necessary visuals
                    self.background_image = self.load_background()
                    self.displayed_territories = self.load_territory_images()
                    self.scale_ui_elements()  # Also rescales buttons/icons based on new heights

                # Handle user interactions
                self.handle_event(event)

            # Update and redraw the board
            self.draw_board()

            # If a user turn is active, display input overlay
            if self.current_overlay:
                self.draw_overlay()

            # **Check for victory condition**
            winner = self.board.check_winner()
            if winner is not None:
                self.draw_game_over_screen(winner)
                pygame.time.delay(5000)  # Display for 5 seconds
                self.running = False  # Exit game loop

            pygame.display.flip()  # Refresh display

        pygame.quit()
