extends Button

signal end_action_pressed(phase: String)

var current_phase := "deploy"

func _ready():
	# Connect the pressed signal
	pressed.connect(_on_pressed)
	
	# Set initial text
	set_phase("deploy")

func set_phase(phase: String):
	"""Updates button text to show 'End [Phase]'"""
	current_phase = phase.to_lower()
	text = "End " + phase.capitalize()
	
	# Optional: Different colors for different phases
	match current_phase:
		"deploy":
			modulate = Color(0.8, 1.0, 0.8)  # Light green
		"attack":
			modulate = Color(1.0, 0.8, 0.8)  # Light red
		"fortify":
			modulate = Color(0.8, 0.8, 1.0)  # Light blue
		_:
			modulate = Color.WHITE

func _on_pressed():
	# Emit signal with current phase
	end_action_pressed.emit(current_phase)
	print("🔘 End button pressed: End", current_phase.capitalize())

func set_enabled(enabled: bool):
	disabled = not enabled
	if disabled:
		modulate.a = 0.5  # Make semi-transparent when disabled
	else:
		modulate.a = 1.0  # Full opacity when enabled
