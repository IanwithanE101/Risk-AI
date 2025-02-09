import os
import tkinter as tk
import pygame
import json
import math
import random
from tkinter import ttk
from Enviornment import territories_with_adjacency

# ----------------------------------------------------------------
# Constants
# ----------------------------------------------------------------
SCREEN_WIDTH, SCREEN_HEIGHT = 1024, 576
BOARD_FOLDER = "RiskBoard"
BACKGROUND_IMAGE_PATH = os.path.join(BOARD_FOLDER, "RiskMap.png")
TERRITORY_MAP_PATH = os.path.join(BOARD_FOLDER, "territory_map.json")
TERRITORY_IMAGES_FOLDER = os.path.join(BOARD_FOLDER, "territories")

with open(TERRITORY_MAP_PATH, "r") as f:
    territory_positions = json.load(f)

# ----------------------------------------------------------------
# Territory
# ----------------------------------------------------------------
class Territory:
    """
    Holds data for a single territory: troop_count, owner, etc.
    A class-level dictionary `all_territories` is used primarily for
    a global set of territory templates (if you wish to keep it).
    """
    all_territories = {}

    def __init__(self, name):
        if name not in territories_with_adjacency:
            return
        self.name = name
        self.troop_count = 0
        self.owner = None
        self.image_path = os.path.join(TERRITORY_IMAGES_FOLDER, f"{name}.png")

        # Optionally store in a global dictionary (if needed).
        Territory.all_territories[name] = self

    def set_owner(self, player_id):
        """Assigns an owner to this territory. Valid players: 1..4 (by default)."""
        if player_id is not None and not (1 <= player_id <= 4):
            raise ValueError("Invalid player ID.")
        self.owner = player_id

    def get_owner(self):
        return self.owner

    def get_image_path(self):
        return self.image_path

    @classmethod
    def initialize_territories(cls):
        """Creates a single global instance of every territory inside the 'all_territories' dict."""
        for name in territories_with_adjacency:
            cls(name)

    @classmethod
    def create_territories_copy(cls):
        """
        Creates and returns a FRESH dictionary of brand-new `Territory` objects
        based on the known territory names in `territories_with_adjacency`.
        """
        new_dict = {}
        for name in territories_with_adjacency:
            new_t = Territory(name)
            new_dict[name] = new_t
        return new_dict

# Initialize the global territory templates (optional).
Territory.initialize_territories()

# ----------------------------------------------------------------
# Board
# ----------------------------------------------------------------
class Board:
    """
    A Board represents a single 'instance' of a Risk board:
      - A fresh dictionary of territories
      - Random ownership assignment
    """
    def __init__(self, num_players=4):
        self.num_players = num_players
        self.territories = {}
        self.generate_board()

    def generate_board(self):
        """
        - Makes a copy of all territories using Territory.create_territories_copy()
        - Randomly assigns each territory among self.num_players owners
        - Sets the troop_count to 1 for each territory
        """
        self.territories = Territory.create_territories_copy()
        territory_names = list(self.territories.keys())
        random.shuffle(territory_names)

        # Distribute as evenly as possible
        total_territories = len(territory_names)
        base_count = total_territories // self.num_players
        remainder = total_territories % self.num_players

        start_idx = 0
        for player_id in range(1, self.num_players + 1):
            # Each player gets at least base_count
            give_this_player = base_count
            # If remainder is still positive, give 1 more
            if remainder > 0:
                give_this_player += 1
                remainder -= 1

            end_idx = start_idx + give_this_player
            chunk = territory_names[start_idx:end_idx]

            # Assign ownership and troop_count = 1
            for territory_name in chunk:
                t = self.territories[territory_name]
                t.set_owner(player_id)
                t.troop_count = 1

            start_idx = end_idx

# ----------------------------------------------------------------
# Arrow
# ----------------------------------------------------------------
class Arrow:
    """
    A simple arrow class to connect two points with lines.
    """
    def __init__(self, start, end, offset_ratio=0.05):
        self.start = start
        self.end = end
        self.offset_ratio = offset_ratio
        self.offset_start, self.offset_end = self.calculate_offsets()

    def calculate_offsets(self):
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        dist = math.sqrt(dx**2 + dy**2)
        if dist == 0:
            return self.start, self.end
        offset = self.offset_ratio * dist
        start = (self.start[0] + offset*(dx/dist), self.start[1] + offset*(dy/dist))
        end = (self.end[0] - offset*(dx/dist),   self.end[1] - offset*(dy/dist))
        return start, end

    def draw(self, screen):
        pygame.draw.line(screen, (0, 0, 0), self.offset_start, self.offset_end, 6)

# ----------------------------------------------------------------
# RiskGameUI
# ----------------------------------------------------------------
class RiskGameUI:
    """
    Encapsulates a Pygame-based Risk board with a sliding overlay.
    Now requires a `Board` instance so that it can draw the territories
    from that board's territory dictionary.
    """
    def __init__(self, board):
        self.board = board  # A Board instance holding the territory objects
        self.window_width = SCREEN_WIDTH
        self.window_height = SCREEN_HEIGHT
        self.running = True

        pygame.init()
        pygame.display.set_caption("Risk Board Game")
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)

        # Background
        self.background_image = pygame.image.load(BACKGROUND_IMAGE_PATH).convert_alpha()
        self.background_image = pygame.transform.scale(self.background_image, (self.window_width, self.window_height))

        # Arrows and territory tracking
        self.arrows = []
        self.start_territory = None
        self.displayed_territories = {}
        self.create_visual_territories()

        # Set window icon (optional)
        self.set_window_icon()

        # Sliding overlay
        self.overlay_height = self.window_height // 12
        self.overlay_y = -self.overlay_height
        self.overlay_text = ""
        self.overlay_state = "hidden"
        self.overlay_start_time = 0
        self.overlay_duration = 1000  # 1 second
        self.overlay_speed = 300      # px/sec

    def set_window_icon(self):
        try:
            icon = pygame.image.load(BACKGROUND_IMAGE_PATH)
            icon = pygame.transform.scale(icon, (32, 32))
            pygame.display.set_icon(icon)
        except Exception as e:
            print(f"Failed to load window icon: {e}")

    def create_visual_territories(self):
        """
        For each Territory in our board, load its image and create a scaled version
        with a rect for Pygame collisions. Store in self.displayed_territories.
        """
        for name, territory in self.board.territories.items():
            try:
                orig_img = pygame.image.load(territory.get_image_path()).convert_alpha()
                scaled_img = pygame.transform.scale(orig_img, (self.window_width, self.window_height))
                rect = scaled_img.get_rect(topleft=(0, 0))
                self.displayed_territories[name] = {
                    "original_image": orig_img,
                    "image": scaled_img,
                    "rect": rect,
                }
            except pygame.error as e:
                print(f"Could not load image for {name}: {e}")

    def show_overlay(self, text):
        self.overlay_text = text
        self.overlay_state = "sliding_down"
        self.overlay_y = -self.overlay_height
        self.overlay_start_time = pygame.time.get_ticks()

    def update_overlay(self, dt):
        now = pygame.time.get_ticks()
        if self.overlay_state == "sliding_down":
            self.overlay_y += self.overlay_speed * (dt / 1000)
            if self.overlay_y >= 0:
                self.overlay_y = 0
                self.overlay_state = "showing"
                self.overlay_start_time = now
        elif self.overlay_state == "showing":
            if now - self.overlay_start_time >= self.overlay_duration:
                self.overlay_state = "sliding_up"
        elif self.overlay_state == "sliding_up":
            self.overlay_y -= self.overlay_speed * (dt / 1000)
            if self.overlay_y <= -self.overlay_height:
                self.overlay_y = -self.overlay_height
                self.overlay_state = "hidden"
                self.overlay_text = ""

    def detect_hover(self):
        """
        Detect if the mouse is over any territory; apply a gray overlay if so.
        Otherwise apply the 'owner' color overlay.
        """
        mouse_pos = pygame.mouse.get_pos()
        hovered = None
        for name, data in self.displayed_territories.items():
            rect = data["rect"]
            if rect.collidepoint(mouse_pos):
                lx = mouse_pos[0] - rect.x
                ly = mouse_pos[1] - rect.y
                pix = data["image"].get_at((lx, ly))
                # If alpha > 0, we are over a non-transparent pixel
                if pix[3] > 0:
                    hovered = name
                    break

        # Now recolor
        for name, data in self.displayed_territories.items():
            if name == hovered:
                self.recolor(name, "gray_overlay")
            else:
                owner_id = self.board.territories[name].get_owner()
                base_color = self.get_color_for_owner(owner_id)
                self.recolor(name, base_color)

    def recolor(self, territory_name, instruction):
        """
        Re-applies color overlay based on either "hover" or territory's ownership.
        """
        if territory_name not in self.displayed_territories:
            return
        data = self.displayed_territories[territory_name]
        orig = data["original_image"]
        scaled = pygame.transform.scale(orig, (self.window_width, self.window_height))

        # Owner color
        owner_id = self.board.territories[territory_name].get_owner()
        owner_color = self.get_color_for_owner(owner_id)

        if instruction == "gray_overlay":
            # Base ownership color first
            base_surf = pygame.Surface(scaled.get_size(), pygame.SRCALPHA)
            base_surf.fill((*owner_color, 150))
            scaled.blit(base_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            # Then the gray "hover" overlay
            gray_surf = pygame.Surface(scaled.get_size(), pygame.SRCALPHA)
            gray_surf.fill((75, 75, 75, 100))
            scaled.blit(gray_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        else:
            # Recolor to the owner color
            overlay_surf = pygame.Surface(scaled.get_size(), pygame.SRCALPHA)
            overlay_surf.fill((*owner_color, 150))
            scaled.blit(overlay_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        data["image"] = scaled

    def get_color_for_owner(self, owner_id):
        color_map = {
            1: (255, 0, 0),       # Red
            2: (0, 255, 0),       # Green
            3: (0, 0, 255),       # Blue
            4: (255, 255, 0),     # Yellow
            None: (255, 255, 255) # White for unowned
        }
        return color_map.get(owner_id, (255, 255, 255))

    def handle_mouse_down(self, mouse_pos):
        for name, data in self.displayed_territories.items():
            rect = data["rect"]
            if rect.collidepoint(mouse_pos):
                lx = mouse_pos[0] - rect.x
                ly = mouse_pos[1] - rect.y
                pix = data["image"].get_at((lx, ly))
                if pix[3] > 0:
                    self.start_territory = name
                    return

    def handle_mouse_up(self, mouse_pos):
        if self.start_territory:
            for name, data in self.displayed_territories.items():
                rect = data["rect"]
                if rect.collidepoint(mouse_pos):
                    lx = mouse_pos[0] - rect.x
                    ly = mouse_pos[1] - rect.y
                    pix = data["image"].get_at((lx, ly))
                    if pix[3] > 0 and name != self.start_territory:
                        sc = self.displayed_territories[self.start_territory]["rect"].center
                        ec = data["rect"].center
                        self.arrows.append(Arrow(sc, ec))
                        break
        self.start_territory = None

    def draw(self):
        # Draw background
        self.screen.blit(self.background_image, (0, 0))
        # Hover detection + recoloring
        self.detect_hover()
        # Draw territories
        for name, d in self.displayed_territories.items():
            self.screen.blit(d["image"], d["rect"])
        # Draw arrows
        for arrow in self.arrows:
            arrow.draw(self.screen)
        # Draw sliding overlay
        if self.overlay_state != "hidden":
            surf = pygame.Surface((self.window_width, self.overlay_height), pygame.SRCALPHA)
            surf.fill((50, 50, 50, 192))
            self.screen.blit(surf, (0, self.overlay_y))
            if self.overlay_text:
                font = pygame.font.SysFont(None, 32)
                text_surf = font.render(self.overlay_text, True, (255, 255, 255))
                text_rect = text_surf.get_rect(center=(self.window_width // 2, self.overlay_y + self.overlay_height // 2))
                self.screen.blit(text_surf, text_rect)
        pygame.display.flip()

    def maintain_aspect_ratio(self, event):
        new_width = event.w
        new_height = int(new_width * (9/16))
        if new_width < 800:
            new_width = 800
            new_height = 450

        # Rescale background
        self.background_image = pygame.transform.scale(
            pygame.image.load(BACKGROUND_IMAGE_PATH).convert_alpha(),
            (new_width, new_height)
        )

        # Rescale territories
        for name, d in self.displayed_territories.items():
            orig = d["original_image"]
            scaled = pygame.transform.scale(orig, (new_width, new_height))
            rect = scaled.get_rect(topleft=(0, 0))
            d["image"] = scaled
            d["rect"] = rect

        self.window_width = new_width
        self.window_height = new_height
        self.screen = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)

        # Reset overlay after resize
        self.overlay_height = self.window_height // 12
        self.overlay_y = -self.overlay_height
        self.overlay_state = "hidden"
        self.overlay_text = ""

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            dt = clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.maintain_aspect_ratio(event)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_mouse_down(pygame.mouse.get_pos())
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.handle_mouse_up(pygame.mouse.get_pos())

            self.update_overlay(dt)
            self.draw()
        pygame.quit()

# ----------------------------------------------------------------
# SlickControlPanelTk
# ----------------------------------------------------------------
class SlickControlPanelTk(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Slick Control Panel")
        self.geometry("900x600")
        self.minsize(600, 400)
        self.resizable(True, True)

        self.style = ttk.Style(self)
        self._configure_style()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.ai_training_tab = ttk.Frame(self.notebook)
        self.play_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.ai_training_tab, text="AI Training")
        self.notebook.add(self.play_tab, text="Play")

        self.build_ai_training_tab()
        self.build_play_tab()

    def _configure_style(self):
        self.style.theme_use("clam")
        self.style.configure("TNotebook", padding=10, background="#eaeaea")
        self.style.configure("TFrame", background="#eaeaea")
        self.style.configure("TLabel", background="#eaeaea", font=("Arial", 12))
        self.style.configure("TButton", font=("Arial", 12), padding=6)
        self.style.configure("TCombobox", font=("Arial", 12))

    def build_ai_training_tab(self):
        lbl = ttk.Label(
            self.ai_training_tab,
            text="AI Training not implemented yet.",
            font=("Arial", 16)
        )
        lbl.pack(pady=20)

    def build_play_tab(self):
        # Gather AI file names
        ai_options = self.get_trained_ai_files()
        self.ai_choices = ["User"] + ai_options

        self.player_combos = []
        self.detail_labels = []

        container = ttk.Frame(self.play_tab)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for i in range(4):
            player_lbl = ttk.Label(container, text=f"Player {i+1}")
            player_lbl.grid(row=i*2, column=0, sticky="w", padx=5, pady=(10, 2))

            # Initialize the StringVar with "User"
            combo_var = tk.StringVar(value="User")
            combo = ttk.Combobox(
                container,
                textvariable=combo_var,
                values=self.ai_choices,
                state="readonly"
            )
            # Force the first item ("User") to be selected in the dropdown
            combo.current(0)

            combo.grid(row=i*2, column=1, sticky="ew", padx=5, pady=(10,2))
            combo.bind("<<ComboboxSelected>>", self.on_player_combo_changed)
            self.player_combos.append(combo)

            # Detail label
            detail_lbl = ttk.Label(container, text=self.get_selection_detail("User"))
            detail_lbl.grid(row=i*2+1, column=0, columnspan=2, sticky="w", padx=5, pady=(0,10))
            self.detail_labels.append(detail_lbl)

        container.columnconfigure(1, weight=1)

        # Play button at bottom-right
        play_btn = ttk.Button(container, text="Play", command=self.launch_4_person_game)
        play_btn.grid(row=8, column=1, sticky="e", padx=5, pady=20)

    def on_player_combo_changed(self, event):
        combo = event.widget
        idx = self.player_combos.index(combo)
        selection = combo.get()
        self.detail_labels[idx].config(text=self.get_selection_detail(selection))

    def get_selection_detail(self, choice):
        if choice == "User":
            return "A human player."
        else:
            return f"Trained AI: {choice}"

    def get_trained_ai_files(self):
        folder = "trained_ai"
        if not os.path.isdir(folder):
            return []
        return [
            f for f in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, f))
        ]

    def launch_4_person_game(self):
        """
        Creates a new Board, which randomizes territory ownership for 4 players,
        then passes that Board to RiskGameUI, which handles all the drawing.
        """
        player_selections = [c.get() for c in self.player_combos]
        print("Starting 4-person game with:", player_selections)

        # Create a new Board with 4 players
        from_board = Board(num_players=4)

        # Launch the Pygame UI, passing the fresh Board
        game_ui = RiskGameUI(board=from_board)
        game_ui.show_overlay("Starting 4-Person Game!")
        game_ui.run()

# ----------------------------------------------------------------
# Main
# ----------------------------------------------------------------
if __name__ == "__main__":
    app = SlickControlPanelTk()
    app.mainloop()
    print("Control Panel closed.")
