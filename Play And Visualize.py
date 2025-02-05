import pygame
import sys
import math
from pygame import mask

class Cube:
    """Represents a cube on the screen."""

    def __init__(self, x, y, size, color_idle, color_highlight, color_invalid, valid=True):
        self.rect = pygame.Rect(x, y, size, size)
        self.color_idle = color_idle
        self.color_highlight = color_highlight
        self.color_invalid = color_invalid  # Color when the cube is invalid
        self.valid = valid  # Whether the cube is a valid target
        self.highlighted = False
        self.clicked = False  # Tracks whether the cube was clicked

    def draw(self, screen):
        """Draw the cube with its current state."""
        if not self.valid:
            color = self.color_invalid if self.is_hovered(pygame.mouse.get_pos()) else self.color_idle
        else:
            color = self.color_highlight if self.highlighted else self.color_idle
        pygame.draw.rect(screen, color, self.rect)

    def is_hovered(self, mouse_pos):
        """Check if the cube is being hovered."""
        return self.rect.collidepoint(mouse_pos)

    def center(self):
        """Get the center of the cube."""
        return self.rect.center


class Arrow:
    """Represents an arrow drawn between two points."""

    def __init__(self, start, end, offset_ratio=0.025):
        self.start = start
        self.end = end
        self.offset_ratio = offset_ratio
        self.offset_start, self.offset_end = self.calculate_offsets()

    def calculate_offsets(self):
        """Calculate the offset points for the arrow."""
        dx, dy = self.end[0] - self.start[0], self.end[1] - self.start[1]
        distance = math.sqrt(dx**2 + dy**2)
        if distance == 0:  # Prevent division by zero
            return self.start, self.end

        offset = self.offset_ratio * distance
        offset_start = (
            self.start[0] + offset * (dx / distance),
            self.start[1] + offset * (dy / distance),
        )
        offset_end = (
            self.end[0] - offset * (dx / distance),
            self.end[1] - offset * (dy / distance),
        )
        return offset_start, offset_end

    def draw(self, screen):
        """Draw the arrow on the screen."""
        pygame.draw.line(screen, (0, 0, 0), self.offset_start, self.offset_end, 3)

        # Arrowhead
        arrow_length = 15
        arrow_angle = 30
        angle = math.atan2(
            self.offset_end[1] - self.offset_start[1],
            self.offset_end[0] - self.offset_start[0],
        )
        x1 = self.offset_end[0] - arrow_length * math.cos(angle + math.radians(arrow_angle))
        y1 = self.offset_end[1] - arrow_length * math.sin(angle + math.radians(arrow_angle))
        x2 = self.offset_end[0] - arrow_length * math.cos(angle - math.radians(arrow_angle))
        y2 = self.offset_end[1] - arrow_length * math.sin(angle - math.radians(arrow_angle))

        pygame.draw.line(screen, (0, 0, 0), self.offset_end, (x1, y1), 3)
        pygame.draw.line(screen, (0, 0, 0), self.offset_end, (x2, y2), 3)


class Game:
    """Main game class."""

    def __init__(self, screen):
        self.screen = screen
        self.cubes = [
            Cube(100, 150, 50, (0, 0, 255), (255, 0, 0), (150, 150, 150), valid=True),  # Valid cube
            Cube(300, 150, 50, (0, 0, 255), (255, 0, 0), (150, 150, 150), valid=True),  # Valid cube
            Cube(500, 150, 50, (0, 0, 255), (255, 0, 0), (150, 150, 150), valid=False),  # Invalid cube
            Cube(700, 150, 50, (0, 0, 255), (255, 0, 0), (150, 150, 150), valid=True),  # Valid cube
        ]
        self.arrows = []
        self.current_drag = None
        self.start_cube = None

    def draw(self):
        """Draw all elements of the game."""
        # Clear screen
        self.screen.fill((255, 255, 255))

        # Draw cubes
        for cube in self.cubes:
            cube.draw(self.screen)

        # Draw arrows
        for arrow in self.arrows:
            arrow.draw(self.screen)

        # Draw the dynamic arrow while dragging
        if self.current_drag:
            self.current_drag.draw(self.screen)

    def reset_highlights(self):
        """Reset all highlights and clicks if no arrows exist."""
        if not self.arrows:
            for cube in self.cubes:
                cube.clicked = False

    def highlight_valid_tiles(self, mouse_pos):
        """Highlight all valid tiles."""
        for cube in self.cubes:
            if cube.valid:
                cube.highlighted = cube.is_hovered(mouse_pos) or cube.clicked

    def update_highlights_from_arrows(self):
        """Keep cubes highlighted if they are part of an arrow."""
        for cube in self.cubes:
            for arrow in self.arrows:
                if cube.center() == arrow.start or cube.center() == arrow.end:
                    cube.highlighted = True

    def handle_mouse_motion(self, mouse_pos):
        """Handle mouse motion events."""
        # Highlight valid tiles
        self.highlight_valid_tiles(mouse_pos)

        # Update the current dragging arrow
        if self.current_drag and self.start_cube:
            self.current_drag.end = mouse_pos
            self.current_drag.offset_start, self.current_drag.offset_end = self.current_drag.calculate_offsets()

    def handle_mouse_down(self, mouse_pos):
        """Handle mouse button down events."""
        # Delete all old lines
        self.arrows.clear()
        self.reset_highlights()  # Reset highlights when clearing arrows

        # Check if clicking on a valid tile to start dragging
        for cube in self.cubes:
            if cube.is_hovered(mouse_pos) and cube.valid:
                self.start_cube = cube
                cube.clicked = True  # Mark cube as clicked
                self.current_drag = Arrow(cube.center(), mouse_pos)
                return

    def handle_mouse_up(self, mouse_pos):
        """Handle mouse button up events."""
        released_on_valid_tile = False  # Track if release was on a valid tile

        if self.start_cube and self.current_drag:
            # Check if releasing on another valid tile
            for cube in self.cubes:
                if cube.is_hovered(mouse_pos) and cube != self.start_cube and cube.valid:
                    # Create a perfect arrow between centers with offset
                    self.arrows.append(Arrow(self.start_cube.center(), cube.center()))
                    cube.clicked = True  # Mark the target cube as clicked
                    released_on_valid_tile = True
                    break

        # If not released on a valid tile, reset the clicked state
        if not released_on_valid_tile and self.start_cube:
            self.start_cube.clicked = False

        # Reset drag state
        self.current_drag = None
        self.start_cube = None

        # Update highlights based on arrows
        self.update_highlights_from_arrows()

    def run(self):
        """Run the game loop."""
        running = True
        while running:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_motion(mouse_pos)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        self.handle_mouse_down(mouse_pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:  # Left mouse button
                        self.handle_mouse_up(mouse_pos)

            self.draw()
            pygame.display.flip()


# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((800, 400))
pygame.display.set_caption("Click and Drag Arrow with Valid and Invalid Tiles")

# Start the game
game = Game(screen)
game.run()

pygame.quit()
sys.exit()



class Cube:
    """Represents a cube on the screen."""

    def __init__(self, x, y, size, color_idle, color_highlight, color_invalid, valid=True):
        self.rect = pygame.Rect(x, y, size, size)
        self.color_idle = color_idle
        self.color_highlight = color_highlight
        self.color_invalid = color_invalid  # Color when the cube is invalid
        self.valid = valid  # Whether the cube is a valid target
        self.highlighted = False
        self.clicked = False  # Tracks whether the cube was clicked

    def draw(self, screen):
        """Draw the cube with its current state."""
        if not self.valid:
            color = self.color_invalid if self.is_hovered(pygame.mouse.get_pos()) else self.color_idle
        else:
            color = self.color_highlight if self.highlighted else self.color_idle
        pygame.draw.rect(screen, color, self.rect)

    def is_hovered(self, mouse_pos):
        """Check if the cube is being hovered."""
        return self.rect.collidepoint(mouse_pos)

    def center(self):
        """Get the center of the cube."""
        return self.rect.center


class Arrow:
    """Represents an arrow drawn between two points."""

    def __init__(self, start, end, offset_ratio=0.025):
        self.start = start
        self.end = end
        self.offset_ratio = offset_ratio
        self.offset_start, self.offset_end = self.calculate_offsets()

    def calculate_offsets(self):
        """Calculate the offset points for the arrow."""
        dx, dy = self.end[0] - self.start[0], self.end[1] - self.start[1]
        distance = math.sqrt(dx**2 + dy**2)
        if distance == 0:  # Prevent division by zero
            return self.start, self.end

        offset = self.offset_ratio * distance
        offset_start = (
            self.start[0] + offset * (dx / distance),
            self.start[1] + offset * (dy / distance),
        )
        offset_end = (
            self.end[0] - offset * (dx / distance),
            self.end[1] - offset * (dy / distance),
        )
        return offset_start, offset_end

    def draw(self, screen):
        """Draw the arrow on the screen."""
        pygame.draw.line(screen, (0, 0, 0), self.offset_start, self.offset_end, 3)

        # Arrowhead
        arrow_length = 15
        arrow_angle = 30
        angle = math.atan2(
            self.offset_end[1] - self.offset_start[1],
            self.offset_end[0] - self.offset_start[0],
        )
        x1 = self.offset_end[0] - arrow_length * math.cos(angle + math.radians(arrow_angle))
        y1 = self.offset_end[1] - arrow_length * math.sin(angle + math.radians(arrow_angle))
        x2 = self.offset_end[0] - arrow_length * math.cos(angle - math.radians(arrow_angle))
        y2 = self.offset_end[1] - arrow_length * math.sin(angle - math.radians(arrow_angle))

        pygame.draw.line(screen, (0, 0, 0), self.offset_end, (x1, y1), 3)
        pygame.draw.line(screen, (0, 0, 0), self.offset_end, (x2, y2), 3)


class Game:
    """Main game class."""

    def __init__(self, screen):
        self.screen = screen
        self.cubes = [
            Cube(100, 150, 50, (0, 0, 255), (255, 0, 0), (150, 150, 150), valid=True),  # Valid cube
            Cube(300, 150, 50, (0, 0, 255), (255, 0, 0), (150, 150, 150), valid=True),  # Valid cube
            Cube(500, 150, 50, (0, 0, 255), (255, 0, 0), (150, 150, 150), valid=False),  # Invalid cube
            Cube(700, 150, 50, (0, 0, 255), (255, 0, 0), (150, 150, 150), valid=True),  # Valid cube
        ]
        self.arrows = []
        self.current_drag = None
        self.start_cube = None

    def draw(self):
        """Draw all elements of the game."""
        # Clear screen
        self.screen.fill((255, 255, 255))

        # Draw cubes
        for cube in self.cubes:
            cube.draw(self.screen)

        # Draw arrows
        for arrow in self.arrows:
            arrow.draw(self.screen)

        # Draw the dynamic arrow while dragging
        if self.current_drag:
            self.current_drag.draw(self.screen)

    def reset_highlights(self):
        """Reset all highlights and clicks if no arrows exist."""
        if not self.arrows:
            for cube in self.cubes:
                cube.clicked = False

    def highlight_valid_tiles(self, mouse_pos):
        """Highlight all valid tiles."""
        for cube in self.cubes:
            if cube.valid:
                cube.highlighted = cube.is_hovered(mouse_pos) or cube.clicked

    def update_highlights_from_arrows(self):
        """Keep cubes highlighted if they are part of an arrow."""
        for cube in self.cubes:
            for arrow in self.arrows:
                if cube.center() == arrow.start or cube.center() == arrow.end:
                    cube.highlighted = True

    def handle_mouse_motion(self, mouse_pos):
        """Handle mouse motion events."""
        # Highlight valid tiles
        self.highlight_valid_tiles(mouse_pos)

        # Update the current dragging arrow
        if self.current_drag and self.start_cube:
            self.current_drag.end = mouse_pos
            self.current_drag.offset_start, self.current_drag.offset_end = self.current_drag.calculate_offsets()

    def handle_mouse_down(self, mouse_pos):
        """Handle mouse button down events."""
        # Delete all old lines
        self.arrows.clear()
        self.reset_highlights()  # Reset highlights when clearing arrows

        # Check if clicking on a valid tile to start dragging
        for cube in self.cubes:
            if cube.is_hovered(mouse_pos) and cube.valid:
                self.start_cube = cube
                cube.clicked = True  # Mark cube as clicked
                self.current_drag = Arrow(cube.center(), mouse_pos)
                return

    def handle_mouse_up(self, mouse_pos):
        """Handle mouse button up events."""
        released_on_valid_tile = False  # Track if release was on a valid tile

        if self.start_cube and self.current_drag:
            # Check if releasing on another valid tile
            for cube in self.cubes:
                if cube.is_hovered(mouse_pos) and cube != self.start_cube and cube.valid:
                    # Create a perfect arrow between centers with offset
                    self.arrows.append(Arrow(self.start_cube.center(), cube.center()))
                    cube.clicked = True  # Mark the target cube as clicked
                    released_on_valid_tile = True
                    break

        # If not released on a valid tile, reset the clicked state
        if not released_on_valid_tile and self.start_cube:
            self.start_cube.clicked = False

        # Reset drag state
        self.current_drag = None
        self.start_cube = None

        # Update highlights based on arrows
        self.update_highlights_from_arrows()

    def run(self):
        """Run the game loop."""
        running = True
        while running:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_motion(mouse_pos)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        self.handle_mouse_down(mouse_pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:  # Left mouse button
                        self.handle_mouse_up(mouse_pos)

            self.draw()
            pygame.display.flip()


# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((800, 400))
pygame.display.set_caption("Click and Drag Arrow with Valid and Invalid Tiles")

# Start the game
game = Game(screen)
game.run()

pygame.quit()
sys.exit()
