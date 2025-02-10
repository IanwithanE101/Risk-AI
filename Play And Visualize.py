import os
import json
import math
import random
import tkinter as tk
import tkinter.messagebox
from tkinter import ttk
import pygame

from PIL import Image, ImageTk

# ----------------------------------------------------------------
# File/Folder Constants
# ----------------------------------------------------------------
BOARD_FOLDER = "RiskBoard"
BACKGROUND_IMAGE_PATH = os.path.join(BOARD_FOLDER, "RiskMap.png")
TERRITORY_MAP_PATH = os.path.join(BOARD_FOLDER, "territory_map.json")
TERRITORY_IMAGES_FOLDER = os.path.join(BOARD_FOLDER, "territories")

CUSTOM_BOARDS_FOLDER = "CustomBoards"  # For saving/loading custom boards

SCREEN_WIDTH, SCREEN_HEIGHT = 1024, 576
PREVIEW_WIDTH, PREVIEW_HEIGHT = 400, 225  # mini UI preview

# ----------------------------------------------------------------
# Attempt to load territory positions
# ----------------------------------------------------------------
if not os.path.exists(TERRITORY_MAP_PATH):
    print(f"WARNING: {TERRITORY_MAP_PATH} not found.")
    territory_positions = {}
else:
    with open(TERRITORY_MAP_PATH, "r") as f:
        territory_positions = json.load(f)

# ----------------------------------------------------------------
# Fallback for territories_with_adjacency
# ----------------------------------------------------------------
try:
    from Enviornment import territories_with_adjacency
except ImportError:
    territories_with_adjacency = {
        "Alaska": [],
        "Northwest_Territory": [],
        # etc...
    }
    print("WARNING: Using a stub for territories_with_adjacency.")


# ----------------------------------------------------------------
# Territory
# ----------------------------------------------------------------
class Territory:
    """
    Represents a single territory with an owner (1..4 or None) and a troop count.
    Territory images are assumed to be white silhouettes on transparent backgrounds.
    """
    all_territories = {}

    def __init__(self, name):
        if name not in territories_with_adjacency:
            return
        self.name = name
        self.troop_count = 0
        self.owner = None
        self.image_path = os.path.join(TERRITORY_IMAGES_FOLDER, f"{name}.png")
        Territory.all_territories[name] = self

    def set_owner(self, player_id):
        if player_id is not None and not (1 <= player_id <= 4):
            raise ValueError("Invalid player ID.")
        self.owner = player_id

    def get_owner(self):
        return self.owner

    def get_image_path(self):
        return self.image_path

    @classmethod
    def initialize_territories(cls):
        for name in territories_with_adjacency:
            cls(name)

    @classmethod
    def create_territories_copy(cls):
        new_dict = {}
        for name in territories_with_adjacency:
            new_t = Territory(name)
            new_dict[name] = new_t
        return new_dict

Territory.initialize_territories()

# ----------------------------------------------------------------
# Board
# ----------------------------------------------------------------
class Board:
    """
    Holds a dict of territories, can randomize or load/save from JSON.
    """
    def __init__(self, num_players=4):
        self.num_players = num_players
        self.territories = {}

    def generate_random_board(self):
        self.territories = Territory.create_territories_copy()
        territory_names = list(self.territories.keys())
        random.shuffle(territory_names)

        total = len(territory_names)
        base_count = total // self.num_players
        remainder = total % self.num_players

        idx = 0
        for player_id in range(1, self.num_players + 1):
            portion = base_count
            if remainder > 0:
                portion += 1
                remainder -= 1

            chunk = territory_names[idx : idx + portion]
            for name in chunk:
                self.territories[name].set_owner(player_id)
                self.territories[name].troop_count = 1
            idx += portion

    def generate_unowned_board(self):
        self.territories = Territory.create_territories_copy()
        for terr in self.territories.values():
            terr.set_owner(None)
            terr.troop_count = 0

    def save_to_file(self, file_path):
        """
        Saves the territory->owner mapping to a JSON file.
        """
        data = {}
        for name, terr in self.territories.items():
            data[name] = terr.get_owner()
        with open(file_path, "w") as f:
            json.dump(data, f)
        print(f"Board saved to {file_path}")

    def load_from_file(self, file_path):
        """
        Loads territory owners from JSON, if they match this board's territory names.
        """
        self.territories = Territory.create_territories_copy()
        if not os.path.exists(file_path):
            print("Board file not found:", file_path)
            return

        with open(file_path, "r") as f:
            data = json.load(f)

        for name, owner in data.items():
            if name in self.territories:
                self.territories[name].set_owner(owner)
                self.territories[name].troop_count = 1 if owner else 0


# ----------------------------------------------------------------
# Main Game (Pygame UI)
# ----------------------------------------------------------------
class RiskGameUI:
    """
    The Pygame-based interface for playing the board.
    Territory images are recolored by overlay on the white silhouettes.
    """
    def __init__(self, board):
        self.board = board
        self.window_width = SCREEN_WIDTH
        self.window_height = SCREEN_HEIGHT
        self.running = True

        pygame.init()
        pygame.display.set_caption("Risk Board Game")
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)

        # Background
        if os.path.exists(BACKGROUND_IMAGE_PATH):
            bg = pygame.image.load(BACKGROUND_IMAGE_PATH).convert_alpha()
            self.background_image = pygame.transform.scale(bg, (self.window_width, self.window_height))
        else:
            self.background_image = pygame.Surface((self.window_width, self.window_height))
            self.background_image.fill((200, 200, 200))

        self.arrows = []
        self.start_territory = None
        self.displayed_territories = {}

        self.create_visual_territories()
        self.set_window_icon()

        # Sliding overlay
        self.overlay_height = self.window_height // 12
        self.overlay_y = -self.overlay_height
        self.overlay_text = ""
        self.overlay_state = "hidden"
        self.overlay_start_time = 0
        self.overlay_duration = 1000  # 1s
        self.overlay_speed = 300      # px/sec

    def set_window_icon(self):
        try:
            icon = pygame.image.load(BACKGROUND_IMAGE_PATH)
            icon = pygame.transform.scale(icon, (32, 32))
            pygame.display.set_icon(icon)
        except Exception as e:
            print(f"Failed to set window icon: {e}")

    def create_visual_territories(self):
        for name, terr in self.board.territories.items():
            path = terr.get_image_path()
            if os.path.exists(path):
                try:
                    orig_img = pygame.image.load(path).convert_alpha()
                    scaled = pygame.transform.scale(orig_img, (self.window_width, self.window_height))
                    rect = scaled.get_rect(topleft=(0, 0))
                    self.displayed_territories[name] = {
                        "original_image": orig_img,  # store the white silhouette
                        "image": scaled,
                        "rect": rect
                    }
                except Exception as e:
                    print(f"Could not load territory {name}: {e}")

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
        mouse_pos = pygame.mouse.get_pos()
        hovered = None
        for name, data in self.displayed_territories.items():
            rect = data["rect"]
            if rect.collidepoint(mouse_pos):
                lx = mouse_pos[0] - rect.x
                ly = mouse_pos[1] - rect.y
                pix = data["image"].get_at((lx, ly))
                if pix[3] > 0:
                    hovered = name
                    break

        for name, data in self.displayed_territories.items():
            if name == hovered:
                self.recolor(name, "gray_overlay")
            else:
                owner_id = self.board.territories[name].get_owner()
                color = self.get_color_for_owner(owner_id)
                self.recolor(name, color)

    def recolor(self, territory_name, instruction):
        """
        If `instruction` is "gray_overlay", do a double overlay
        (owner color, then gray).
        Otherwise, assume it's an (R,G,B) color tuple.
        """
        if territory_name not in self.displayed_territories:
            return

        data = self.displayed_territories[territory_name]
        orig = data["original_image"]
        base = pygame.transform.scale(orig, (self.window_width, self.window_height))

        owner_id = self.board.territories[territory_name].get_owner()
        owner_color = self.get_color_for_owner(owner_id)

        if instruction == "gray_overlay":
            # Color overlay with stronger green tint
            c_surf = pygame.Surface(base.get_size(), pygame.SRCALPHA)
            c_surf.fill((*owner_color, 200))  # Stronger green tint
            base.blit(c_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            # Softer gray overlay to desaturate slightly but not overpower green
            g_surf = pygame.Surface(base.get_size(), pygame.SRCALPHA)
            g_surf.fill((100, 100, 100, 80))  # Lighter gray, lower alpha
            base.blit(g_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        else:
            # instruction is presumably a (R,G,B) tuple
            overlay = pygame.Surface(base.get_size(), pygame.SRCALPHA)
            overlay.fill((*instruction, 180))
            base.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        data["image"] = base

    def get_color_for_owner(self, owner_id):
        color_map = {
            1: (255, 0, 0),
            2: (0, 255, 0),
            3: (0, 0, 255),
            4: (255, 255, 0),
            None: (255, 255, 255)
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
        self.screen.blit(self.background_image, (0, 0))
        self.detect_hover()
        for _, d in self.displayed_territories.items():
            self.screen.blit(d["image"], d["rect"])

        for arrow in self.arrows:
            arrow.draw(self.screen)

        if self.overlay_state != "hidden":
            surf = pygame.Surface((self.window_width, self.overlay_height), pygame.SRCALPHA)
            surf.fill((50, 50, 50, 192))
            self.screen.blit(surf, (0, self.overlay_y))
            if self.overlay_text:
                font = pygame.font.SysFont(None, 32)
                text_surf = font.render(self.overlay_text, True, (255, 255, 255))
                text_rect = text_surf.get_rect(center=(self.window_width//2, self.overlay_y + self.overlay_height//2))
                self.screen.blit(text_surf, text_rect)

        pygame.display.flip()

    def maintain_aspect_ratio(self, event):
        new_width = event.w
        new_height = int(new_width * (9/16))
        if new_width < 800:
            new_width = 800
            new_height = 450

        if os.path.exists(BACKGROUND_IMAGE_PATH):
            bg = pygame.image.load(BACKGROUND_IMAGE_PATH).convert_alpha()
            self.background_image = pygame.transform.scale(bg, (new_width, new_height))
        else:
            self.background_image = pygame.Surface((new_width, new_height))
            self.background_image.fill((200,200,200))

        for name, d in self.displayed_territories.items():
            orig = d["original_image"]
            scaled = pygame.transform.scale(orig, (new_width, new_height))
            rect = scaled.get_rect(topleft=(0, 0))
            d["image"] = scaled
            d["rect"] = rect

        self.window_width = new_width
        self.window_height = new_height
        self.screen = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)

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
# Arrow
# ----------------------------------------------------------------
class Arrow:
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
# MiniBoardPreview
# ----------------------------------------------------------------
class MiniBoardPreview(tk.Frame):
    """
    A small frame inside Tkinter that displays a scaled-down Risk map
    plus tinted territory silhouettes. Clicking a territory cycles ownership.
    """
    def __init__(self, parent, board, width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT):
        super().__init__(parent)
        self.board = board
        self.width = width
        self.height = height

        self.bg_image = None
        self.territory_images = {}  # name->PIL territory image
        self.preview_image = None
        self.tk_preview = None

        self.load_background()
        self.load_territories()

        self.label = tk.Label(self)
        self.label.pack()
        self.label.bind("<Button-1>", self.on_click)

        self.update_preview()

    def load_background(self):
        if os.path.exists(BACKGROUND_IMAGE_PATH):
            pil_bg = Image.open(BACKGROUND_IMAGE_PATH).convert("RGBA")
            pil_bg = pil_bg.resize((self.width, self.height), Image.Resampling.LANCZOS)
            self.bg_image = pil_bg
        else:
            self.bg_image = Image.new("RGBA", (self.width, self.height), (255,255,255,255))

    def load_territories(self):
        for name, terr in self.board.territories.items():
            p = terr.get_image_path()
            if os.path.exists(p):
                try:
                    pil_img = Image.open(p).convert("RGBA")
                    pil_img = pil_img.resize((self.width, self.height), Image.Resampling.LANCZOS)
                    self.territory_images[name] = pil_img
                except Exception as e:
                    print(f"Could not load territory {name}: {e}")

    def update_preview(self):
        """
        Composites each territory onto the background.
        We do a pixel loop looking for white (255,255,255)
        and recolor those based on the owner.
        """
        if self.bg_image is None:
            base = Image.new("RGBA", (self.width, self.height), (255,255,255,255))
        else:
            base = self.bg_image.copy()

        for name, terr in self.board.territories.items():
            if name not in self.territory_images:
                continue
            t_img = self.territory_images[name].copy()

            color = self.get_color_for_owner(terr.get_owner())
            px = t_img.load()
            w,h = t_img.size
            for x in range(w):
                for y in range(h):
                    r,g,b,a = px[x,y]
                    if a > 0 and (r,g,b) == (255,255,255):
                        px[x,y] = (color[0], color[1], color[2], a)

            base.alpha_composite(t_img)

        self.preview_image = base
        self.tk_preview = ImageTk.PhotoImage(base)
        self.label.config(image=self.tk_preview)
        self.label.image = self.tk_preview  # keep reference

    def on_click(self, event):
        x, y = event.x, event.y
        # check from top territory down
        for name in reversed(list(self.territory_images.keys())):
            img = self.territory_images[name]
            if 0 <= x < self.width and 0 <= y < self.height:
                r,g,b,a = img.getpixel((x,y))
                if a > 0:
                    # user clicked inside this territory
                    curr = self.board.territories[name].get_owner()
                    new_owner = self.next_owner(curr)
                    self.board.territories[name].set_owner(new_owner)
                    self.update_preview()
                    break

    def next_owner(self, curr):
        if curr is None:
            return 1
        elif curr == 4:
            return None
        else:
            return curr + 1

    def get_color_for_owner(self, owner_id):
        color_map = {
            1: (255, 0, 0),
            2: (0, 255, 0),
            3: (0, 0, 255),
            4: (255, 255, 0),
            None: (255, 255, 255)
        }
        return color_map.get(owner_id, (255,255,255))


# ----------------------------------------------------------------
# SlickControlPanelTk
# ----------------------------------------------------------------
class SlickControlPanelTk(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Slick Control Panel")
        self.geometry("641x736")
        self.minsize(641, 736)

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
        self.style.configure("TFrame", background="#eaeaea")
        self.style.configure("TLabel", background="#eaeaea", font=("Arial", 12))
        self.style.configure("TButton", font=("Arial", 12), padding=6)
        self.style.configure("TCombobox", font=("Arial", 12), fieldbackground="white", foreground="black")
        self.style.configure("Switch.TCheckbutton", indicatoron=False, relief="ridge", padding=6)

    def build_ai_training_tab(self):
        lbl = ttk.Label(self.ai_training_tab, text="AI Training not implemented yet.", font=("Arial", 16))
        lbl.pack(pady=20)

    def build_play_tab(self):
        container = ttk.Frame(self.play_tab)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Player selection from directory
        self.ai_choices = ["User"] + self.get_trained_ai_files()
        self.player_combos = []
        self.detail_labels = []

        for i in range(4):
            lbl = ttk.Label(container, text=f"Player {i+1}")
            lbl.grid(row=i*2, column=0, sticky="w", padx=5, pady=2)

            combo = ttk.Combobox(container, state="readonly", values=self.ai_choices)
            combo.set(self.ai_choices[0])  # Force first item selection
            combo.grid(row=i*2, column=1, sticky="ew", padx=5, pady=2)
            self.player_combos.append(combo)

            det_lbl = ttk.Label(container, text="A human player.")
            det_lbl.grid(row=i*2+1, column=0, columnspan=2, sticky="w", padx=5, pady=2)
            self.detail_labels.append(det_lbl)

        # Use Custom Board switch
        self.use_custom_board_var = tk.BooleanVar()
        custom_board_switch = ttk.Checkbutton(
            container, text="Use Custom Board", variable=self.use_custom_board_var,
            style="Switch.TCheckbutton", command=self.toggle_custom_board
        )
        custom_board_switch.grid(row=9, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        # Mini Board Preview Frame
        self.custom_board_frame = ttk.Frame(container)
        self.custom_board_frame.grid(row=10, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
        self.custom_board_frame.grid_remove()

        # Board name input
        lbl_board_name = ttk.Label(container, text="Board Name:")
        lbl_board_name.grid(row=11, column=0, sticky="w", padx=5, pady=5)

        self.board_name_var = tk.StringVar()
        board_name_entry = ttk.Entry(container, textvariable=self.board_name_var)
        board_name_entry.grid(row=11, column=1, sticky="ew", padx=5, pady=5)

        # Load button next to Saved Board dropdown
        lbl_saved_board = ttk.Label(container, text="Saved Board:")
        lbl_saved_board.grid(row=12, column=0, sticky="w", padx=5, pady=5)

        self.saved_board_var = tk.StringVar(value="None")
        self.saved_board_combo = ttk.Combobox(container, textvariable=self.saved_board_var, values=self.get_saved_boards_list(), state="readonly")
        self.saved_board_combo.grid(row=12, column=1, sticky="ew", padx=5, pady=5)

        load_btn = ttk.Button(container, text="Load", command=self.load_board)
        load_btn.grid(row=12, column=2, sticky="w", padx=5, pady=5)

        # Play button anchored to bottom-right
        self.play_btn = ttk.Button(container, text="Play", command=self.start_game)
        self.play_btn.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)

        container.columnconfigure(1, weight=1)

    def get_trained_ai_files(self):
        if not os.path.isdir("TrainedAI"):
            return []
        return sorted(
            f for f in os.listdir("TrainedAI")
            if os.path.isfile(os.path.join("TrainedAI", f))
        )

    def get_saved_boards_list(self):
        if not os.path.isdir(CUSTOM_BOARDS_FOLDER):
            os.makedirs(CUSTOM_BOARDS_FOLDER, exist_ok=True)
            return []
        return [f for f in os.listdir(CUSTOM_BOARDS_FOLDER) if f.endswith(".json")]

    def toggle_custom_board(self):
        if self.use_custom_board_var.get():
            self.custom_board_frame.grid()
            for child in self.custom_board_frame.winfo_children():
                child.destroy()

            self.custom_board = Board(num_players=4)
            self.custom_board.generate_random_board()

            tk.Label(self.custom_board_frame, text="Customize Territories Below:").pack(pady=5)
            preview = MiniBoardPreview(self.custom_board_frame, board=self.custom_board)
            preview.pack()
        else:
            self.custom_board_frame.grid_remove()
            self.custom_board = None

    def load_board(self):
        chosen = self.saved_board_var.get()
        if chosen == "None":
            tk.messagebox.showwarning("No Board Selected", "Please select a board from the dropdown.")
            return

        path = os.path.join(CUSTOM_BOARDS_FOLDER, chosen)
        if not os.path.exists(path):
            tk.messagebox.showerror("Error", f"File not found: {path}")
            return

        self.use_custom_board_var.set(True)
        self.custom_board_frame.grid()

        self.custom_board = Board(num_players=4)
        self.custom_board.load_from_file(path)

        for child in self.custom_board_frame.winfo_children():
            child.destroy()

        tk.Label(self.custom_board_frame, text=f"Editing Board: {chosen}").pack(pady=5)
        preview = MiniBoardPreview(self.custom_board_frame, board=self.custom_board)
        preview.pack()

    def start_game(self):
        # Determine which board to use
        if self.use_custom_board_var.get() and hasattr(self, 'custom_board'):
            game_board = self.custom_board
        else:
            # Generate a new random board
            game_board = Board(num_players=4)
            game_board.generate_random_board()

        # Determine players (example placeholder)
        players = [combo.get() for combo in self.player_combos]
        print("Starting game with players:", players)

        # Launch the Pygame UI
        game_ui = RiskGameUI(game_board)
        game_ui.run()

# ----------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(CUSTOM_BOARDS_FOLDER, exist_ok=True)
    app = SlickControlPanelTk()
    app.mainloop()
    print("Control Panel closed.")
