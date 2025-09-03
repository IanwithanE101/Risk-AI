# This should be in end_button.gd

extends Button

signal end_action_pressed(phase: String)

var current_phase := "deploy"
var enabled := false

func _ready():
	pressed.connect(_on_pressed)
	set_enabled(false)  # Start disabled

func _on_pressed():
	if not enabled:
		return
	
	print("🔘 End button pressed: End", current_phase.capitalize())
	
	# Emit the signal with the current phase
	end_action_pressed.emit(current_phase)
	
	# Disable until next action
	set_enabled(false)

func set_phase(phase: String):
	"""Updates the button text based on current phase."""
	current_phase = phase
	match phase:
		"deploy":
			text = "End Deploy"
		"attack":
			text = "End Attack"
		"fortify":
			text = "End Fortify"
		_:
			text = "End Phase"

func set_enabled(is_enabled: bool):
	"""Enables or disables the button."""
	enabled = is_enabled
	disabled = not is_enabled
	
	if is_enabled:
		modulate.a = 1.0  # Full opacity
	else:
		modulate.a = 0.5  # Half opacity when disabled
