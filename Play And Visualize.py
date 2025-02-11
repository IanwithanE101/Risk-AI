import os
import json
import math
import random
import tkinter as tk
import tkinter.messagebox
from tkinter import ttk
import pygame
import pygame_menu
import pygame_menu.locals

from PIL import Image, ImageTk

# ----------------------------------------------------------------
# File/Folder Constants
# ----------------------------------------------------------------
BOARD_FOLDER = "RiskBoard"
BACKGROUND_IMAGE_PATH = os.path.join(BOARD_FOLDER, "RiskMap.png")
TERRITORY_MAP_PATH = os.path.join(BOARD_FOLDER, "territory_map.json")
TERRITORY_IMAGES_FOLDER = os.path.join(BOARD_FOLDER, "territories")
mapjson = os.path.join(BOARD_FOLDER, "territory_map.json")

# Read and parse the territory_map.json file and put it into a dictionary
with open(mapjson, "r") as file:
    territory_positions = json.load(file)

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
class RiskGameGUI:
    """
    The Pygame-based interface for playing the board.
    We separate:
      - draw_board(): can show board w/ hover, troop counts, etc.
      - draw_game(): the full live rendering used in the main loop.

    When the deploy menu is open, we do one final call to draw_board()
    then run menu.mainloop(...) so the game effectively 'pauses'
    (no main-loop updates until the user closes the menu).
    """

    def __init__(self, board, player_types, territory_positions):
        self.board = board
        self.player_types = player_types  # e.g. ["User","User","AI","User"]
        self.territory_positions = territory_positions  # from territory_map.json
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

        # Phases
        self.phases = ["deploy", "attack", "fortify"]
        self.current_phase_index = 0
        self.current_phase = self.phases[self.current_phase_index]
        self.current_player = 1

        # Example troop logic
        self.troops_remaining = 5
        self.ask_deploy_confirm = True
        self.show_deploy_confirm_box = False

        # Territory images
        self.displayed_territories = {}
        self.create_visual_territories()

        # For "deploy-phase valid dictionary"
        self.deploy_valid_territories = set()

        # Arrow-mode tracking
        self.arrow_segments = []
        self.arrow_mode = False
        self.arrow_start_territory = None
        self.valid_territories_for_arrow = []

        # Overlay & Buttons
        self.default_overlay_duration = 1500
        self.overlay_height = self.window_height // 12
        self.overlay_y = -self.overlay_height
        self.overlay_text = ""
        self.overlay_state = "hidden"
        self.overlay_start_time = 0
        self.overlay_duration = self.default_overlay_duration
        self.overlay_speed = 300

        # End turn button (always gold)
        self.end_turn_button_rect = pygame.Rect(self.window_width - 140, self.window_height - 50, 130, 40)

        self.set_window_icon()

        # Welcome overlay
        self.show_overlay("Welcome to RISK!", duration=self.default_overlay_duration * 2)

        # pygame_menu placeholders for deploy
        self.deploy_menu = None
        self.deploy_menu_territory = None

    # ------------------------------
    #  PHASE / TURN
    # ------------------------------
    def next_phase(self):
        self.current_phase_index += 1
        if self.current_phase_index >= len(self.phases):
            self.current_phase_index = 0
            self.current_player += 1
            if self.current_player > 4:
                self.current_player = 1

        self.current_phase = self.phases[self.current_phase_index]
        if self.current_phase == "deploy":
            self.troops_remaining = 5  # Example logic
            self.init_deploy_valid_territories()
        else:
            self.deploy_valid_territories.clear()

        self.show_overlay(f"Player {self.current_player}: {self.current_phase.capitalize()} Phase")

    def init_deploy_valid_territories(self):
        self.deploy_valid_territories.clear()
        for name, terr in self.board.territories.items():
            if terr.get_owner() == self.current_player:
                self.deploy_valid_territories.add(name)

    # ------------------------------
    #  TERRITORY IMAGES
    # ------------------------------
    def create_visual_territories(self):
        for name, terr in self.board.territories.items():
            path = terr.get_image_path()
            if os.path.exists(path):
                try:
                    orig_img = pygame.image.load(path).convert_alpha()
                    scaled = pygame.transform.scale(orig_img, (self.window_width, self.window_height))
                    rect = scaled.get_rect(topleft=(0, 0))
                    self.displayed_territories[name] = {
                        "original_image": orig_img,
                        "image": scaled,
                        "rect": rect
                    }
                except Exception as e:
                    print(f"Could not load territory {name} from {path}: {e}")
            else:
                print(f"No image found for territory {name} at {path}")

    # ------------------------------
    #  HELPER METHODS
    # ------------------------------
    def set_window_icon(self):
        try:
            if os.path.exists(BACKGROUND_IMAGE_PATH):
                icon = pygame.image.load(BACKGROUND_IMAGE_PATH).convert_alpha()
                icon = pygame.transform.scale(icon, (32, 32))
                pygame.display.set_icon(icon)
        except Exception as e:
            print(f"Failed to set window icon: {e}")

    def get_color_for_owner(self, owner_id):
        color_map = {
            1: (255, 0, 0),
            2: (0, 255, 0),
            3: (0, 0, 255),
            4: (255, 255, 0),
            None: (255, 255, 255)
        }
        return color_map.get(owner_id, (255, 255, 255))

    # ------------------------------
    #  OVERLAYS
    # ------------------------------
    def show_overlay(self, text, duration=None):
        self.overlay_text = text
        self.overlay_state = "sliding_down"
        self.overlay_y = -self.overlay_height
        self.overlay_start_time = pygame.time.get_ticks()
        if duration is not None:
            self.overlay_duration = duration
        else:
            self.overlay_duration = self.default_overlay_duration

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

    def show_deploy_confirm_popup(self):
        self.show_deploy_confirm_box = True

    def hide_deploy_confirm_popup(self):
        self.show_deploy_confirm_box = False

    # ------------------------------
    #  ARROW MODE
    # ------------------------------
    def set_arrow_mode(self, start_territory, valid_territories):
        self.arrow_mode = True
        self.arrow_start_territory = start_territory
        self.valid_territories_for_arrow = valid_territories

    def create_arrow_segment(self, start_pos, end_pos, offset_ratio=0.1):
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        dist = math.sqrt(dx ** 2 + dy ** 2)
        if dist == 0:
            offset_start = start_pos
            offset_end = end_pos
        else:
            offset = offset_ratio * dist
            offset_start = (
                start_pos[0] + offset * (dx / dist),
                start_pos[1] + offset * (dy / dist),
            )
            offset_end = (
                end_pos[0] - offset * (dx / dist),
                end_pos[1] - offset * (dy / dist),
            )
        self.arrow_segments.append((offset_start, offset_end))

    # ------------------------------
    #  HOVER & RECOLOR
    # ------------------------------
    def detect_hover(self):
        """
        If arrow_mode is off, hovering recolors territory with gray overlay.
        If arrow_mode is on, valid targets are gray, invalid are red.
        """
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
            owner_id = self.board.territories[name].get_owner()
            if self.arrow_mode:
                if name == hovered:
                    if name in self.valid_territories_for_arrow:
                        self.recolor(name, "gray_overlay")
                    else:
                        self.recolor(name, (255, 0, 0))
                else:
                    color = self.get_color_for_owner(owner_id)
                    self.recolor(name, color)
            else:
                if name == hovered:
                    self.recolor(name, "gray_overlay")
                else:
                    color = self.get_color_for_owner(owner_id)
                    self.recolor(name, color)

    def recolor(self, territory_name, instruction):
        if territory_name not in self.displayed_territories:
            return

        data = self.displayed_territories[territory_name]
        orig = data["original_image"]
        base = pygame.transform.scale(orig, (self.window_width, self.window_height))

        owner_id = self.board.territories[territory_name].get_owner()
        owner_color = self.get_color_for_owner(owner_id)

        if instruction == "gray_overlay":
            c_surf = pygame.Surface(base.get_size(), pygame.SRCALPHA)
            c_surf.fill((*owner_color, 200))
            base.blit(c_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            g_surf = pygame.Surface(base.get_size(), pygame.SRCALPHA)
            g_surf.fill((100, 100, 100, 80))
            base.blit(g_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        else:
            # assume an (R,G,B) tuple
            overlay = pygame.Surface(base.get_size(), pygame.SRCALPHA)
            overlay.fill((*instruction, 180))
            base.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        data["image"] = base

    # ------------------------------
    #  PYGAME_MENU: DEPLOY TROOPS
    # ------------------------------
    def open_deploy_menu(self, territory_name):
        """
        Creates a pygame_menu sub-menu, but does not do a sub-loop.
        We do one final draw_board() (including hover if you want),
        then call menu.mainloop(...) so the main loop is effectively paused.
        """
        # 1) Draw the board one last time with hover if you want
        self.draw_board(with_hover=True)
        pygame.display.flip()

        # 2) Setup the menu
        self.deploy_menu_territory = territory_name
        max_amt = self.troops_remaining
        amount_options = list(range(max_amt, 0, -1))

        custom_theme = pygame_menu.themes.THEME_DARK.copy()
        custom_theme.background_color = (30, 30, 30, 180)
        custom_theme.widget_font_size = 20
        custom_theme.title_font_size = 24

        menu_width, menu_height = 400, 300
        self.deploy_menu = pygame_menu.Menu(
            title=f"Deploy to {territory_name}",
            width=menu_width,
            height=menu_height,
            theme=custom_theme
        )

        select_items = [(str(x), x) for x in amount_options]
        self.deploy_menu_selector = self.deploy_menu.add.dropselect(
            title="Troops to deploy:",
            items=select_items,
            default=0,
            selection_box_height=5,
            selection_box_width=100,
            dropselect_position=pygame_menu.locals.POSITION_SOUTH,
            placeholder_add_to_selection_box=False
        )
        self.deploy_menu.add.button("Deploy", self.on_deploy_menu_confirm)
        self.deploy_menu.add.button("Cancel", self.on_deploy_menu_cancel)

        # 3) Block the game with menu.mainloop. The user sees the board behind it.
        self.deploy_menu.mainloop(self.screen)

        # Once .mainloop() returns => user pressed Deploy or Cancel => game resumes

    def on_deploy_menu_confirm(self):
        selected_item = self.deploy_menu_selector.get_value()
        if not selected_item:
            return
        deploy_amount = selected_item[0][1]
        terr = self.board.territories[self.deploy_menu_territory]
        terr.troop_count += deploy_amount
        self.troops_remaining -= deploy_amount
        print(f"Deployed {deploy_amount} troops to {self.deploy_menu_territory}. "
              f"Remaining: {self.troops_remaining}")
        self.deploy_menu.disable()

    def on_deploy_menu_cancel(self):
        self.deploy_menu.disable()
        print("Cancelled deploy menu")

    # ------------------------------
    #  DRAWING UTILS
    # ------------------------------
    def draw_territory_troop_counts(self):
        font = pygame.font.SysFont(None, 20)
        ratio_x = self.window_width / 512.0
        ratio_y = self.window_height / 288.0

        for name, terr in self.board.territories.items():
            if name not in self.territory_positions:
                continue
            x_orig = self.territory_positions[name]["x"]
            y_orig = self.territory_positions[name]["y"]
            draw_x = int(x_orig * ratio_x)
            draw_y = int(y_orig * ratio_y)

            text = str(terr.troop_count)
            text_surf = font.render(text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(draw_x, draw_y))
            self.screen.blit(text_surf, text_rect)

    def draw_board(self, with_hover=False):
        """
        A single draw of the board. If with_hover=True, we call detect_hover first
        so territories recolor under the mouse.
        This can be used to show a final snapshot with territory highlights, if desired.
        """
        if with_hover:
            self.detect_hover()
        else:
            # If we skip detect_hover, everything is normal-colored
            for name, d in self.displayed_territories.items():
                # Reset territory color to owner
                owner_id = self.board.territories[name].get_owner()
                color = self.get_color_for_owner(owner_id)
                self.recolor(name, color)

        self.screen.blit(self.background_image, (0, 0))

        for _, d in self.displayed_territories.items():
            self.screen.blit(d["image"], d["rect"])

        self.draw_territory_troop_counts()

    def draw_game(self):
        """
        The 'live' draw that includes hover detection, arrows, overlays, etc.
        Called in the normal main loop to update the game each frame.
        """
        self.screen.blit(self.background_image, (0, 0))
        self.detect_hover()

        # Blit territory silhouettes
        for _, d in self.displayed_territories.items():
            self.screen.blit(d["image"], d["rect"])

        # Draw arrows
        for segment in self.arrow_segments:
            pygame.draw.line(self.screen, (0, 0, 0), segment[0], segment[1], 6)

        # End turn button
        self.draw_end_turn_button()

        # Old "deploy confirm" box, if any
        if self.show_deploy_confirm_box:
            self.draw_deploy_confirm_popup()

        # Troop counts
        self.draw_territory_troop_counts()

        # Overlay
        if self.overlay_state != "hidden":
            surf = pygame.Surface((self.window_width, self.overlay_height), pygame.SRCALPHA)
            surf.fill((50, 50, 50, 192))
            self.screen.blit(surf, (0, self.overlay_y))
            if self.overlay_text:
                font = pygame.font.SysFont(None, 32)
                text_surf = font.render(self.overlay_text, True, (255, 255, 255))
                text_rect = text_surf.get_rect(center=(self.window_width//2, self.overlay_y + self.overlay_height//2))
                self.screen.blit(text_surf, text_rect)

    def draw_end_turn_button(self):
        color = (255, 215, 0)
        pygame.draw.rect(self.screen, color, self.end_turn_button_rect)
        font = pygame.font.SysFont(None, 24)
        phase_label = f"End {self.current_phase.capitalize()}"
        label_surf = font.render(phase_label, True, (0, 0, 0))
        label_rect = label_surf.get_rect(center=self.end_turn_button_rect.center)
        self.screen.blit(label_surf, label_rect)

    def draw_deploy_confirm_popup(self):
        rect = self.get_deploy_popup_rect()
        pygame.draw.rect(self.screen, (220, 220, 220), rect, border_radius=8)
        pygame.draw.rect(self.screen, (50, 50, 50), rect, width=2, border_radius=8)

        font = pygame.font.SysFont(None, 22)
        txt1 = f"You still have {self.troops_remaining} troops to deploy."
        txt2 = "Do you still want to end the turn?"
        line1 = font.render(txt1, True, (0, 0, 0))
        line2 = font.render(txt2, True, (0, 0, 0))

        self.screen.blit(line1, (rect.x + 20, rect.y + 15))
        self.screen.blit(line2, (rect.x + 20, rect.y + 40))

        yes_rect = pygame.Rect(rect.x + 40, rect.y + 80, 60, 30)
        no_rect = pygame.Rect(rect.x + 120, rect.y + 80, 60, 30)
        pygame.draw.rect(self.screen, (150, 150, 150), yes_rect)
        pygame.draw.rect(self.screen, (150, 150, 150), no_rect)
        yes_label = font.render("Yes", True, (0, 0, 0))
        no_label = font.render("No", True, (0, 0, 0))
        self.screen.blit(yes_label, yes_label.get_rect(center=yes_rect.center))
        self.screen.blit(no_label, no_label.get_rect(center=no_rect.center))

        checkbox_rect = pygame.Rect(rect.x + 20, rect.y + 120, 20, 20)
        pygame.draw.rect(self.screen, (255, 255, 255), checkbox_rect)
        pygame.draw.rect(self.screen, (0, 0, 0), checkbox_rect, width=1)

        if not self.ask_deploy_confirm:
            pygame.draw.line(self.screen, (0,0,0), (checkbox_rect.x, checkbox_rect.y),
                             (checkbox_rect.right, checkbox_rect.bottom), width=2)
            pygame.draw.line(self.screen, (0,0,0), (checkbox_rect.x, checkbox_rect.bottom),
                             (checkbox_rect.right, checkbox_rect.y), width=2)

        cb_label = font.render("Don't ask again", True, (0,0,0))
        self.screen.blit(cb_label, (checkbox_rect.x + 30, checkbox_rect.y - 2))

    def get_deploy_popup_rect(self):
        w, h = 280, 160
        x = (self.window_width - w) // 2
        y = (self.window_height - h) // 2
        return pygame.Rect(x, y, w, h)

    # ------------------------------
    #  EVENT HANDLERS
    # ------------------------------
    def handle_mouse_down(self, mouse_pos):
        # If AI turn => ignore
        if self.player_types[self.current_player - 1] != "User":
            return

        # If in deploy phase, user clicked territory => open deploy menu
        if self.current_phase == "deploy" and not self.arrow_mode:
            for name, data in self.displayed_territories.items():
                rect = data["rect"]
                if rect.collidepoint(mouse_pos):
                    lx = mouse_pos[0] - rect.x
                    ly = mouse_pos[1] - rect.y
                    pix = data["image"].get_at((lx, ly))
                    if pix[3] > 0:
                        if name not in self.deploy_valid_territories:
                            print(f"Invalid territory for deploy: {name}")
                            return
                        # Open the menu => draws board, calls menu.mainloop
                        self.open_deploy_menu(name)
                        return

        # If end turn button?
        if self.end_turn_button_rect.collidepoint(mouse_pos):
            self.handle_end_turn_button_click()
            return

        # If old confirm popup is showing
        if self.show_deploy_confirm_box:
            self.handle_deploy_popup_click(mouse_pos)
            return

        # If arrow mode
        if self.arrow_mode:
            pass

    def handle_mouse_up(self, mouse_pos):
        if self.player_types[self.current_player - 1] != "User":
            return

        # arrow finalization
        if self.arrow_mode and self.arrow_start_territory:
            end_territory = None
            for name, data in self.displayed_territories.items():
                rect = data["rect"]
                if rect.collidepoint(mouse_pos):
                    lx = mouse_pos[0] - rect.x
                    ly = mouse_pos[1] - rect.y
                    pix = data["image"].get_at((lx, ly))
                    if pix[3] > 0:
                        end_territory = name
                        break

            if end_territory and end_territory in self.valid_territories_for_arrow:
                sc = self.displayed_territories[self.arrow_start_territory]["rect"].center
                ec = self.displayed_territories[end_territory]["rect"].center
                self.create_arrow_segment(sc, ec)

            self.arrow_mode = False
            self.arrow_start_territory = None
            self.valid_territories_for_arrow = []

    def handle_end_turn_button_click(self):
        if self.current_phase == "deploy":
            if self.troops_remaining > 0 and self.ask_deploy_confirm:
                self.show_deploy_confirm_popup()
            else:
                self.next_phase()
        else:
            self.next_phase()

    def handle_deploy_popup_click(self, mouse_pos):
        popup_rect = self.get_deploy_popup_rect()
        yes_rect = pygame.Rect(popup_rect.x + 40, popup_rect.y + 80, 60, 30)
        no_rect = pygame.Rect(popup_rect.x + 120, popup_rect.y + 80, 60, 30)
        checkbox_rect = pygame.Rect(popup_rect.x + 20, popup_rect.y + 120, 20, 20)

        if yes_rect.collidepoint(mouse_pos):
            self.hide_deploy_confirm_popup()
            self.next_phase()
        elif no_rect.collidepoint(mouse_pos):
            self.hide_deploy_confirm_popup()
        elif checkbox_rect.collidepoint(mouse_pos):
            self.ask_deploy_confirm = not self.ask_deploy_confirm

    # ------------------------------
    #  MAIN LOOP
    # ------------------------------
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
            self.background_image.fill((200, 200, 200))

        # Rescale territory silhouettes
        for name, d in self.displayed_territories.items():
            orig = d["original_image"]
            scaled = pygame.transform.scale(orig, (new_width, new_height))
            rect = scaled.get_rect(topleft=(0, 0))
            d["image"] = scaled
            d["rect"] = rect

        self.window_width = new_width
        self.window_height = new_height
        self.screen = pygame.display.set_mode((new_width, new_height), pygame.RESIZABLE)

        # Update button rect
        self.end_turn_button_rect = pygame.Rect(self.window_width - 140, self.window_height - 50, 130, 40)

        # Reset overlay
        self.overlay_height = self.window_height // 12
        self.overlay_y = -self.overlay_height
        self.overlay_state = "hidden"
        self.overlay_text = ""

    def run(self):
        clock = pygame.time.Clock()

        if self.current_phase == "deploy":
            self.init_deploy_valid_territories()
        self.show_overlay(f"Player {self.current_player}: {self.current_phase.capitalize()} Phase")

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

            # Normal game updates
            self.update_overlay(dt)
            self.draw_game()  # includes detect_hover, arrows, overlays, etc.
            pygame.display.flip()

        pygame.quit()


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
# MainMenu
# ----------------------------------------------------------------
class MainMenu(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Risk AI Main Menu")
        self.geometry("641x736")
        self.minsize(641, 736)

        self.set_window_icon()

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

        # Add Save button here
        save_btn = ttk.Button(container, text="Save", command=self.save_board)
        save_btn.grid(row=11, column=2, sticky="w", padx=5, pady=5)  # Added Save button

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

    def set_window_icon(self):
        """Sets the window icon using the RiskMap image."""
        try:
            if os.path.exists(BACKGROUND_IMAGE_PATH):
                img = Image.open(BACKGROUND_IMAGE_PATH)
                img = img.resize((32, 32), Image.Resampling.LANCZOS)
                icon = ImageTk.PhotoImage(img)
                self.iconphoto(False, icon)
        except Exception as e:
            print(f"Failed to set window icon: {e}")

    def save_board(self):
        """Saves the current custom board with the specified name"""
        board_name = self.board_name_var.get().strip()

        if not board_name:
            tk.messagebox.showerror("Error", "Please enter a board name")
            return

        if not hasattr(self, 'custom_board') or not self.custom_board:
            tk.messagebox.showerror("Error", "No custom board to save!\nEnable 'Use Custom Board' first")
            return

        # Ensure directory exists
        os.makedirs(CUSTOM_BOARDS_FOLDER, exist_ok=True)

        # Add JSON extension if missing
        if not board_name.endswith('.json'):
            board_name += '.json'

        file_path = os.path.join(CUSTOM_BOARDS_FOLDER, board_name)

        try:
            self.custom_board.save_to_file(file_path)
            # Update saved boards list and select new entry
            self.saved_board_combo['values'] = self.get_saved_boards_list()
            self.saved_board_var.set(board_name)
            tk.messagebox.showinfo("Success", f"Board saved as {board_name}")
        except Exception as e:
            tk.messagebox.showerror("Save Error", f"Failed to save board:\n{str(e)}")

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
            game_board = Board(num_players=4)
            game_board.generate_random_board()

        players = [combo.get() for combo in self.player_combos]
        print("Starting game with players:", players)

        # Pass in territory_positions
        game_gui = RiskGameGUI(game_board, players, territory_positions)
        game_gui.run()


# ----------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(CUSTOM_BOARDS_FOLDER, exist_ok=True)
    app = MainMenu()
    app.mainloop()
    print("Control Panel closed.")
