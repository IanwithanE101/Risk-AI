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

# Attack phase specific
var is_selected_attacker := false
var is_valid_target := false
var is_adjacent_to_attacker := false
var adjacent_territories := []  # List of adjacent territory names

func _ready():
	print("🔍 TERRITORY ", name, ": _ready() called - Script is attached and running!")
	idx = start_colour_index
	sprite.texture = texture
	_apply_colour()
	_update_troop_label()
	connect("mouse_entered", _on_enter)
	connect("mouse_exited", _on_exit)
	connect("input_event", _on_input)
	
	# Initialize adjacency list (you'll need to set this based on your game data)
	_initialize_adjacency()
	print("🔍 TERRITORY ", name, ": All signals connected")

func _initialize_adjacency():
	"""Initialize the adjacent territories list based on game rules."""
	# This should be populated from your game configuration
	# For now, we'll get it from a parent node or leave empty
	pass

func set_adjacency(adjacent_list: Array):
	"""Sets the list of adjacent territories."""
	adjacent_territories = adjacent_list

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
	
	# Handle mouse button press (start of click-hold for attack)
	if ev is InputEventMouseButton and ev.button_index == MOUSE_BUTTON_LEFT:
		if ev.pressed:
			_handle_mouse_down()
		else:
			_handle_mouse_up()

func _handle_mouse_down():
	"""Handles mouse button press - starts attack selection."""
	match current_phase:
		"deploy":
			_handle_deploy_click()
		"attack":
			_handle_attack_mouse_down()
		"fortify":
			print("🏰 Fortify phase click on", name, "(not implemented)")
		_:
			# Default behavior (cycle colors)
			idx = (idx + 1) % colours.size()
			_apply_colour()

func _handle_mouse_up():
	"""Handles mouse button release - completes attack if valid."""
	if current_phase == "attack":
		_handle_attack_mouse_up()

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

func _handle_attack_mouse_down():
	"""Handles mouse down during attack phase - selects attacker."""
	if territory_owner == current_player and troop_count > 1:
		# Valid attacker selection
		print("⚔️ Selected attacker:", name)
		_notify_attack_selection_start()
		is_selected_attacker = true
		# Notify all territories about the selection
		_broadcast_attacker_selected()
	else:
		print("❌ Cannot attack from this territory")

func _handle_attack_mouse_up():
	"""Handles mouse up during attack phase - executes attack if valid."""
	if is_valid_target:
		var attacker = _get_selected_attacker()
		if attacker:
			print("🎯 Attacking from", attacker.name, "to", name)
			_notify_attack_execution(attacker.name, name)
	
	# Clear attack state for all territories
	_broadcast_clear_attack_state()

func _notify_attack_selection_start():
	"""Notifies the controls about attack selection starting."""
	var controls = get_parent().get_parent().get_node_or_null("Controls")
	if controls and controls.has_method("start_attack_selection"):
		controls.start_attack_selection(name, global_position)

func _notify_attack_execution(from_territory: String, to_territory: String):
	"""Notifies the controls about attack execution."""
	var controls = get_parent().get_parent().get_node_or_null("Controls")
	if controls and controls.has_method("execute_attack"):
		controls.execute_attack(from_territory, to_territory)

func _broadcast_attacker_selected():
	"""Notifies all territories that this one was selected as attacker."""
	var territories = get_parent().get_children()
	for territory in territories:
		if territory.has_method("set_attack_context"):
			territory.set_attack_context(name, adjacent_territories)

func _broadcast_clear_attack_state():
	"""Clears attack state for all territories."""
	var territories = get_parent().get_children()
	for territory in territories:
		if territory.has_method("clear_attack_state"):
			territory.clear_attack_state()

func _get_selected_attacker():
	"""Finds the currently selected attacker territory."""
	var territories = get_parent().get_children()
	for territory in territories:
		if territory.is_selected_attacker:
			return territory
	return null

func set_attack_context(attacker_name: String, attacker_adjacents: Array):
	"""Sets the attack context when another territory is selected as attacker."""
	if name == attacker_name:
		is_selected_attacker = true
		is_valid_target = false
		is_adjacent_to_attacker = false
	elif name in attacker_adjacents:
		is_selected_attacker = false
		is_adjacent_to_attacker = true
		# Valid target if adjacent and not owned by current player
		is_valid_target = (territory_owner != current_player)
	else:
		is_selected_attacker = false
		is_adjacent_to_attacker = false
		is_valid_target = false
	
	# Update visuals
	_apply_colour()

func clear_attack_state():
	"""Clears all attack-related state."""
	is_selected_attacker = false
	is_valid_target = false
	is_adjacent_to_attacker = false
	_apply_colour()

func _apply_phase_hover():
	"""Applies hover effects based on current phase."""
	match current_phase:
		"deploy":
			_apply_deploy_hover()
		"attack":
			_apply_attack_hover()
		"fortify":
			_apply_fortify_hover()
		_:
			_apply_colour()  # Default hover

func _apply_deploy_hover():
	"""Applies deploy phase hover effects."""
	if territory_owner == current_player:
		# Our territory - highlight in bright green
		sprite.modulate = Color(0.4, 1.0, 0.4)  # Bright green highlight
	else:
		# Enemy territory - redden
		sprite.modulate = Color(1.0, 0.4, 0.4)  # Red tint

func _apply_attack_hover():
	"""Applies attack phase hover effects."""
	# During attack selection (mouse held down)
	if _get_selected_attacker():
		if is_selected_attacker:
			# The selected attacker - keep bright
			sprite.modulate = colours[idx]
		elif is_valid_target and hovered:
			# Valid target - green when hovered
			sprite.modulate = Color(0.4, 1.0, 0.4)
		elif is_adjacent_to_attacker and hovered:
			# Invalid adjacent - red when hovered
			sprite.modulate = Color(1.0, 0.4, 0.4)
		else:
			# Non-adjacent or not hovered - dimmed/white
			sprite.modulate = Color(0.5, 0.5, 0.5)
	else:
		# Normal attack phase hover (no selection)
		if territory_owner == current_player and troop_count > 1:
			# Potential attacker - highlight
			sprite.modulate = Color(0.7, 0.7, 1.0) if hovered else colours[idx]
		else:
			sprite.modulate = colours[idx]

func _apply_fortify_hover():
	"""Applies fortify phase hover effects."""
	# Similar to deploy but for fortify logic
	if territory_owner == current_player:
		sprite.modulate = Color(0.4, 0.4, 1.0) if hovered else colours[idx]
	else:
		sprite.modulate = colours[idx]

func _apply_colour():
	"""Applies the base color with phase-specific modifications."""
	if current_phase == "attack" and _get_selected_attacker():
		_apply_attack_hover()
	elif hovered:
		_apply_phase_hover()
	else:
		sprite.modulate = colours[idx]

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
