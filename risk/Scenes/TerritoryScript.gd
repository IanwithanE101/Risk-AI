extends Area2D

@export var texture:Texture2D         # assign PNG per territory
@export var dim_amount := 0.8
@export var colours := [
	Color(0.8, 0.2, 0.2),  # Darker Red
	Color(0.2, 0.4, 0.8),  # Darker Blue  
	Color(0.2, 0.6, 0.2),  # Darker Green
	Color(0.8, 0.8, 0.2),  # Darker Yellow
	Color(0.9, 0.9, 0.9)   # Light Gray (instead of pure white)
]
@export var start_colour_index := 4   # start on white by default

@export var x_offset := 0
@export var y_offset := 0

var idx := 0
var hovered := false
var interaction_enabled := true

@onready var sprite := $Sprite2D
@onready var troop_label := $TroopLabel

@export var troop_count: int = 0

# Game state tracking
var current_phase := ""
var current_player := 0
var territory_owner := 0

func _ready():
	print("🔍 TERRITORY ", name, ": _ready() called - Script is attached and running!")
	idx = start_colour_index
	sprite.texture = texture
	_apply_colour()
	_update_troop_label()
	connect("mouse_entered", _on_enter)
	connect("mouse_exited", _on_exit)
	connect("input_event", _on_input)
	print("🔍 TERRITORY ", name, ": All signals connected")

func _on_enter():
	if not interaction_enabled:
		return
		
	hovered = true
	_apply_phase_hover()

func _on_exit():
	if not interaction_enabled:
		return
		
	hovered = false
	_apply_colour()

func _on_input(_v, ev, _s):
	if not interaction_enabled:
		return
		
	if ev is InputEventMouseButton and ev.button_index == MOUSE_BUTTON_LEFT and ev.pressed:
		_handle_click()

func _handle_click():
	"""Handles territory clicks based on current phase."""
	match current_phase:
		"deploy":
			_handle_deploy_click()
		"attack":
			print("🗡️ Attack phase click on", name, "(not implemented)")
		"fortify":
			print("🏰 Fortify phase click on", name, "(not implemented)")
		_:
			# Default behavior (cycle colors)
			idx = (idx + 1) % colours.size()
			_apply_colour()

func _handle_deploy_click():
	"""Handles clicks during deploy phase."""
	if territory_owner == current_player:
		# This is our territory - open deploy popup
		print("🪖 Clicked own territory:", name, "- opening deploy popup")
		var controls = get_parent().get_parent().get_node_or_null("Controls")
		if controls and controls.has_method("territory_clicked"):
			controls.territory_clicked(name, territory_owner)
	else:
		print("❌ Cannot deploy to enemy territory:", name)

func _apply_phase_hover():
	"""Applies hover effects based on current phase."""
	match current_phase:
		"deploy":
			_apply_deploy_hover()
		_:
			_apply_colour()  # Default hover

func _apply_deploy_hover():
	"""Applies deploy phase hover effects."""
	var base: Color = colours[idx]
	
	if territory_owner == current_player:
		# Our territory - highlight in bright green
		sprite.modulate = Color(0.4, 1.0, 0.4)  # Bright green highlight
	else:
		# Enemy territory - redden
		sprite.modulate = Color(1.0, 0.4, 0.4)  # Red tint

func _apply_colour():
	"""Applies the base color with optional hover dimming."""
	var base: Color = colours[idx]
	if hovered and current_phase == "":
		# Only apply default hover when not in a specific phase
		sprite.modulate = base.darkened(1.0 - dim_amount)
	else:
		sprite.modulate = base

func update_owner(owner_id: int, troops: int = -1):
	"""Updates territory owner and optionally troop count."""
	print("🏰 Updating territory ", name, " - Owner:", owner_id, " Troops:", troops)
	
	# Store owner for phase logic
	territory_owner = owner_id if owner_id != null else 0
	
	# Update owner color
	if owner_id == null or owner_id == 0:
		idx = start_colour_index  # Return to default/unowned color
	else:
		idx = clamp(owner_id - 1, 0, colours.size() - 1)
	
	_apply_colour()
	
	# Update troop count if provided
	if troops >= 0:
		troop_count = troops
		_update_troop_label()
		print("✅ Territory ", name, " updated - Owner: ", owner_id, " Troops: ", troop_count)

func update_troop_count(new_count: int):
	"""Updates only the troop count."""
	troop_count = new_count
	_update_troop_label()
	print("🪖 Territory ", name, " troop count updated to: ", troop_count)

func update_game_state(phase: String, player: int):
	"""Updates the territory's knowledge of current game state."""
	current_phase = phase
	current_player = player
	print("🎯 Territory ", name, " updated - Phase: ", phase, " Current Player: ", player)

func set_interaction_enabled(enabled: bool):
	"""Enables or disables territory interactions."""
	interaction_enabled = enabled
	if not enabled:
		hovered = false
		_apply_colour()

func _update_troop_label():
	"""Updates the troop count label visibility and text."""
	if troop_label:
		troop_label.text = str(troop_count)
		# Only show if there are troops
		troop_label.visible = troop_count > 0
