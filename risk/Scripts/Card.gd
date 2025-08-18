# Card.gd - Latest complete Risk territory card script
@tool
extends Control
class_name Card

# INSPECTOR EDITABLE PROPERTIES
@export var card_territory_name: String = "Territory Name" : set = set_territory_name_inspector
@export_enum("Infantry", "Cavalry", "Artillery", "Wildcard") var card_background_type: String = "Infantry" : set = set_background_type_inspector

# Card visual components
@onready var territory_label: Label = $TerritoryLabel
@onready var infantry_image: TextureRect = $InfantryImage
@onready var cavalry_image: TextureRect = $CavalryImage  
@onready var artillery_image: TextureRect = $ArtilleryImage
@onready var wildcard_image: TextureRect = $WildcardImage

# Card data
var territory_name: String = ""
var card_type: String = ""
var is_selected: bool = false
var card_id: int = -1

# Visual settings - can be set by parent manager
var default_size: Vector2 = Vector2(150, 200)
var selected_color: Color = Color.YELLOW
var normal_color: Color = Color.WHITE
var hover_color: Color = Color.LIGHT_GRAY

# Glow effect settings
var is_clicked: bool = false
var is_hovered: bool = false

# Signals for parent management
signal card_clicked(card: Card)
signal card_hover_started(card: Card)
signal card_hover_ended(card: Card)
signal card_selected_changed(card: Card, selected: bool)

func _ready():
	# Set initial size
	custom_minimum_size = default_size
	size = default_size
	
	# Hide all card images initially
	hide_all_images()
	
	# Apply inspector settings
	update_from_inspector()
	
	# Connect mouse signals for interactivity
	mouse_entered.connect(_on_mouse_entered)
	mouse_exited.connect(_on_mouse_exited)
	gui_input.connect(_on_gui_input)
	
	# Set up Control node styling directly
	modulate = normal_color

func hide_all_images():
	"""Hide all card type images"""
	pass  # No longer used - using z-ordering instead

func set_card_data(territory: String, troop_type: String, id: int = -1):
	"""Set the card's territory and type, then update visuals"""
	territory_name = territory
	card_type = troop_type
	card_id = id
	
	# Format territory name nicely and fit to label
	var display_name = territory.replace("_", " ")
	fit_text_to_label(territory_label, display_name, 18, 8)
	
	# Show appropriate card image
	match troop_type:
		"Infantry":
			if infantry_image: infantry_image.visible = true
		"Cavalry": 
			if cavalry_image: cavalry_image.visible = true
		"Artillery":
			if artillery_image: artillery_image.visible = true
		"Wildcard":
			if wildcard_image: wildcard_image.visible = true
		_:
			print("Warning: Unknown card type: ", troop_type)

func fit_text_to_label(label: Label, text: String, max_font_size: int = 18, min_font_size: int = 8):
	"""Automatically adjusts font size to fit text within label bounds"""
	if not label:
		return
		
	label.text = text
	var available_size = label.get_rect().size
	var current_font_size = max_font_size
	
	while current_font_size >= min_font_size:
		label.add_theme_font_size_override("font_size", current_font_size)
		label.reset_size()
		
		if label.get_content_height() <= available_size.y:
			break
		
		current_font_size -= 1
	
	current_font_size = max(current_font_size, min_font_size)
	label.add_theme_font_size_override("font_size", current_font_size)

func set_card_size(new_size: Vector2):
	"""Set the card to a specific size - called by parent manager"""
	custom_minimum_size = new_size
	size = new_size
	default_size = new_size
	
	# Re-fit text after resize
	if territory_label and territory_name != "":
		var display_name = territory_name.replace("_", " ")
		fit_text_to_label(territory_label, display_name, 18, 8)

func set_selected(selected: bool):
	"""Set selection state - called by parent manager"""
	if is_selected == selected:
		return
		
	is_selected = selected
	update_visual_state()
	card_selected_changed.emit(self, is_selected)

func update_visual_state():
	"""Updates visual appearance based on current state"""
	if is_selected:
		modulate = selected_color
		var style = StyleBoxFlat.new()
		style.bg_color = selected_color
		style.border_width_left = 3
		style.border_width_right = 3
		style.border_width_top = 3
		style.border_width_bottom = 3
		style.border_color = Color.GOLD
		add_theme_stylebox_override("panel", style)
	else:
		modulate = normal_color
		remove_theme_stylebox_override("panel")

func get_territory_name() -> String:
	return territory_name
	
func get_card_type() -> String:  
	return card_type

func get_card_id() -> int:
	return card_id

func get_is_selected() -> bool:
	return is_selected

# Mouse interaction handlers
func _on_mouse_entered():
	is_hovered = true
	update_glow_effect()
	if not is_selected:
		modulate = hover_color
	card_hover_started.emit(self)

func _on_mouse_exited():
	is_hovered = false
	update_glow_effect()
	if not is_selected:
		modulate = normal_color
	card_hover_ended.emit(self)

func _on_gui_input(event: InputEvent):
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
			# Toggle clicked state
			is_clicked = !is_clicked
			update_glow_effect()
			
			card_clicked.emit(self)
			notify_general_ui_of_click()

# Utility methods for parent managers
func set_colors(normal: Color, hover: Color, selected: Color):
	"""Allow parent to customize colors"""
	normal_color = normal
	hover_color = hover
	selected_color = selected
	update_visual_state()

func set_interactable(interactable: bool):
	"""Enable/disable card interactions"""
	mouse_filter = Control.MOUSE_FILTER_IGNORE if not interactable else Control.MOUSE_FILTER_PASS

func animate_to_position(target_position: Vector2, duration: float = 0.3):
	"""Smooth animation to new position - useful for card collection rearrangement"""
	var tween = create_tween()
	tween.tween_property(self, "position", target_position, duration)
	tween.tween_callback(func(): pass)

func animate_scale(target_scale: Vector2, duration: float = 0.2):
	"""Animate card scaling - useful for selection effects"""
	var tween = create_tween()
	tween.tween_property(self, "scale", target_scale, duration)

# OBJECT-LIKE INTERFACE METHODS
func set_card_type(type: String):
	"""Set card type programmatically - acts like an object method"""
	if type in ["Infantry", "Cavalry", "Artillery", "Wildcard"]:
		card_background_type = type
		card_type = type
		update_card_display()
	else:
		print("ERROR: Invalid card type: ", type)

func set_card_name(name: String):
	"""Set card name programmatically - acts like an object method"""
	card_territory_name = name
	territory_name = name
	update_territory_label()

func set_card_invisible():
	"""Make the entire card invisible"""
	visible = false

func set_card_visible():
	"""Make the entire card visible"""
	visible = true

func setup_card(name: String, type: String):
	"""Complete card setup in one call"""
	set_card_name(name)
	set_card_type(type)

# COMMUNICATION WITH PARENT GENERALUI
func notify_general_ui_of_click():
	"""Communicate up the hierarchy to GeneralUI"""
	var general_ui = get_node("../../../../../../")
	if general_ui and general_ui.has_method("on_card_clicked"):
		general_ui.on_card_clicked(self)
		print("Card: Notified GeneralUI of click - ", get_territory_name())
	else:
		print("Could not find GeneralUI or on_card_clicked method")

# GLOW EFFECT SYSTEM
func update_glow_effect():
	"""Update the glow based on current state"""
	if is_clicked:
		apply_glow(Color.WHITE, 4, 1.0)
	elif is_hovered:
		apply_glow(Color.WHITE, 2, 0.6)
	else:
		remove_glow()

func apply_glow(glow_color: Color, border_width: int, intensity: float):
	"""Apply glow effect with specified parameters"""
	var style = StyleBoxFlat.new()
	style.bg_color = Color.TRANSPARENT
	style.border_color = glow_color * intensity
	style.border_width_left = border_width
	style.border_width_right = border_width
	style.border_width_top = border_width
	style.border_width_bottom = border_width
	style.shadow_color = glow_color * (intensity * 0.5)
	style.shadow_size = border_width
	style.shadow_offset = Vector2.ZERO
	
	add_theme_stylebox_override("panel", style)

func remove_glow():
	"""Remove glow effect"""
	remove_theme_stylebox_override("panel")

func set_clicked_state(clicked: bool):
	"""Manually set the clicked state (for external control)"""
	is_clicked = clicked
	update_glow_effect()

# INSPECTOR SETTER METHODS
func set_territory_name_inspector(value: String):
	card_territory_name = value
	territory_name = value
	call_deferred("update_territory_label")

func set_background_type_inspector(value: String):
	card_background_type = value
	card_type = value
	call_deferred("update_card_display")

func update_territory_label():
	if not territory_label:
		territory_label = get_node_or_null("TerritoryLabel")
		if not territory_label:
			print("ERROR: Could not find TerritoryLabel!")
			return
	
	var display_name = card_territory_name.replace("_", " ")
	territory_label.text = display_name
	move_child(territory_label, get_child_count() - 1)

func update_from_inspector():
	update_territory_label()
	update_card_display()

func update_card_display():
	# Find nodes if not already found
	if not infantry_image: infantry_image = get_node_or_null("InfantryImage")
	if not cavalry_image: cavalry_image = get_node_or_null("CavalryImage")
	if not artillery_image: artillery_image = get_node_or_null("ArtilleryImage")
	if not wildcard_image: wildcard_image = get_node_or_null("WildcardImage")
	
	if not infantry_image or not cavalry_image or not artillery_image or not wildcard_image:
		print("ERROR: Some image nodes missing!")
		return
	
	# Move selected image to front
	var target_image: TextureRect = null
	match card_background_type:
		"Infantry": target_image = infantry_image
		"Cavalry": target_image = cavalry_image
		"Artillery": target_image = artillery_image
		"Wildcard": target_image = wildcard_image
	
	if target_image:
		move_child(target_image, get_child_count() - 2)
		if territory_label:
			move_child(territory_label, get_child_count() - 1)

func _to_string() -> String:
	return "Card[%s:%s, ID:%d, Selected:%s]" % [territory_name, card_type, card_id, is_selected]
