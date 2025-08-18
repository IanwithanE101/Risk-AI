extends Node

# UI References - use Node instead of Control to avoid type errors
var deploy_controls: Node
var attack_controls: Node  
var fortify_controls: Node
var troop_deploy_popup: PopupPanel  # Changed from Control to PopupPanel
var feedback_label: Label
var troop_selection_label: Label
var troop_slider: HSlider
var confirm_button: Button
var cancel_button: Button

# Game state
var current_phase := ""
var current_player := 0
var troops_to_deploy := 0
var selected_territory := ""
var risk_client: Node

func _ready():
	print("🔍 CONTROLS: _ready() called")
	print("🔍 CONTROLS: My parent is: ", get_parent().name)
	
	# Find child control scenes
	deploy_controls = get_node_or_null("deploy_controls")
	attack_controls = get_node_or_null("attack_controls") 
	fortify_controls = get_node_or_null("fortify_controls")
	
	# Find UI elements within deploy_controls
	if deploy_controls:
		print("✅ CONTROLS: Found deploy_controls")
		troop_deploy_popup = deploy_controls.get_node_or_null("TroopDeployPopup")
		feedback_label = deploy_controls.get_node_or_null("Feedback")
		troop_selection_label = deploy_controls.get_node_or_null("TroopDeployPopup/TroopSelectionLabel")
		troop_slider = deploy_controls.get_node_or_null("TroopDeployPopup/TroopSlider")
		confirm_button = deploy_controls.get_node_or_null("TroopDeployPopup/ConfirmButton")
		cancel_button = deploy_controls.get_node_or_null("TroopDeployPopup/CancelButton")
	else:
		print("❌ CONTROLS: deploy_controls child not found!")
	
	# Get reference to risk client - RiskClient is the parent of Controls
	risk_client = get_parent()  # Controls is child of Main, which has RiskClient.gd attached
	if risk_client and risk_client.has_method("request_troop_income"):
		print("✅ CONTROLS: Found RiskClient as parent")
	else:
		print("❌ CONTROLS: Could not find RiskClient methods in parent!")
	
	# Connect popup buttons
	if confirm_button:
		confirm_button.pressed.connect(_on_confirm_deploy)
		print("✅ CONTROLS: Connected confirm button")
	if cancel_button:
		cancel_button.pressed.connect(_on_cancel_deploy)
		print("✅ CONTROLS: Connected cancel button")
	
	# Connect slider
	if troop_slider:
		troop_slider.value_changed.connect(_on_slider_changed)
		print("✅ CONTROLS: Connected troop slider")
	
	# Start with all controls hidden
	hide_all_controls()

func hide_all_controls():
	"""Hides all phase controls."""
	print("🔍 CONTROLS: Hiding all controls")
	if deploy_controls:
		deploy_controls.visible = false
		print("🔍 CONTROLS: Hidden deploy_controls")
	else:
		print("❌ CONTROLS: deploy_controls node not found!")
	
	if attack_controls:
		attack_controls.visible = false
		print("🔍 CONTROLS: Hidden attack_controls")
	else:
		print("❌ CONTROLS: attack_controls node not found!")
	
	if fortify_controls:
		fortify_controls.visible = false
		print("🔍 CONTROLS: Hidden fortify_controls")
	else:
		print("❌ CONTROLS: fortify_controls node not found!")
	
	if troop_deploy_popup:
		troop_deploy_popup.visible = false
		print("🔍 CONTROLS: Hidden troop_deploy_popup")
	else:
		print("❌ CONTROLS: troop_deploy_popup node not found!")

func activate_phase(phase: String, player: int):
	"""Activates controls for the given phase."""
	current_phase = phase
	current_player = player
	
	print("🎮 CONTROLS: Activating controls for phase:", phase, "player:", player)
	
	# Hide all controls first
	hide_all_controls()
	
	match phase:
		"deploy":
			activate_deploy_phase()
		"attack":
			activate_attack_phase()
		"fortify":
			activate_fortify_phase()

func activate_deploy_phase():
	"""Activates deploy phase controls."""
	print("🪖 CONTROLS: Activating deploy phase")
	
	if deploy_controls:
		deploy_controls.visible = true
	
	# Keep popup hidden initially
	if troop_deploy_popup:
		troop_deploy_popup.visible = false
	
	# Request troop income from server
	if risk_client and risk_client.has_method("request_troop_income"):
		print("🔍 CONTROLS: Requesting troop income from RiskClient")
		risk_client.request_troop_income(current_player)
	else:
		print("❌ CONTROLS: Cannot request troop income - RiskClient method missing")
	
	# Update feedback label
	update_feedback_label()

func activate_attack_phase():
	"""Activates attack phase controls (placeholder)."""
	print("⚔️ CONTROLS: Activating attack phase (not implemented)")
	if attack_controls:
		attack_controls.visible = true

func activate_fortify_phase():
	"""Activates fortify phase controls (placeholder)."""
	print("🏰 CONTROLS: Activating fortify phase (not implemented)")
	if fortify_controls:
		fortify_controls.visible = true

func set_troops_to_deploy(amount: int):
	"""Sets the number of troops available to deploy."""
	troops_to_deploy = amount
	print("💰 CONTROLS: Set troops to deploy:", troops_to_deploy)
	update_feedback_label()
	check_end_phase_button()

func update_feedback_label():
	"""Updates the feedback label with current troop count."""
	if feedback_label:
		feedback_label.text = "Troops to Deploy: " + str(troops_to_deploy)

func check_end_phase_button():
	"""Enables/disables end phase button based on remaining troops."""
	# End button is now in GeneralUI, so find it there
	var end_button = get_parent().get_node_or_null("GeneralUI/End_Button")
	if end_button and end_button.has_method("set_enabled"):
		if troops_to_deploy > 0:
			end_button.set_enabled(false)  # Disable if troops remain
			print("🚫 CONTROLS: End phase button disabled - troops remaining:", troops_to_deploy)
		else:
			end_button.set_enabled(true)   # Enable if no troops remain
			print("✅ CONTROLS: End phase button enabled - no troops remaining")
	else:
		print("❌ CONTROLS: Could not find end button at GeneralUI/End_Button")

func open_deploy_popup(territory_name: String):
	"""Opens the troop deployment popup for the selected territory."""
	if troops_to_deploy <= 0:
		print("❌ CONTROLS: No troops available to deploy!")
		return
	
	selected_territory = territory_name
	print("🎯 CONTROLS: Opening deploy popup for territory:", territory_name)
	
	if troop_deploy_popup:
		troop_deploy_popup.visible = true
	
	# Set up slider
	if troop_slider:
		troop_slider.max_value = troops_to_deploy
		troop_slider.value = troops_to_deploy  # Start at maximum
		_on_slider_changed(troops_to_deploy)  # Update label immediately

func _on_slider_changed(value: float):
	"""Updates troop selection label when slider changes."""
	if troop_selection_label:
		troop_selection_label.text = str(int(value))

func _on_confirm_deploy():
	"""Confirms troop deployment."""
	if not selected_territory or not troop_slider:
		print("❌ CONTROLS: No territory selected or slider not found!")
		return
	
	var troops_selected = int(troop_slider.value)
	print("✅ CONTROLS: Confirming deploy:", troops_selected, "troops to", selected_territory)
	
	# Send deploy command to server
	if risk_client and risk_client.has_method("send_deploy_troops"):
		risk_client.send_deploy_troops(current_player, selected_territory, troops_selected)
	
	# Close popup
	close_deploy_popup()

func _on_cancel_deploy():
	"""Cancels troop deployment."""
	print("❌ CONTROLS: Cancelled deploy")
	close_deploy_popup()

func close_deploy_popup():
	"""Closes the deploy popup and resets selection."""
	if troop_deploy_popup:
		troop_deploy_popup.visible = false
	
	selected_territory = ""
	
	# Re-enable territory interactions
	var territories_node = get_parent().get_node_or_null("Territories")
	if territories_node:
		for territory in territories_node.get_children():
			if territory.has_method("set_interaction_enabled"):
				territory.set_interaction_enabled(true)

func handle_deploy_response(success: bool, territory: String, troops: int):
	"""Handles response from server about deployment."""
	if success:
		print("✅ CONTROLS: Deploy successful:", troops, "troops to", territory)
		# Subtract from available troops
		troops_to_deploy -= troops
		update_feedback_label()
		check_end_phase_button()
	else:
		print("❌ CONTROLS: Deploy failed for territory:", territory)

# Method that territories can call to open deploy popup
func territory_clicked(territory_name: String, territory_owner: int):
	"""Called when a territory is clicked during deploy phase."""
	if current_phase != "deploy":
		return
	
	if territory_owner != current_player:
		print("❌ CONTROLS: Can only deploy to your own territories!")
		return
	
	# Disable territory interactions while popup is open
	var territories_node = get_parent().get_node_or_null("Territories")
	if territories_node:
		for territory in territories_node.get_children():
			if territory.has_method("set_interaction_enabled"):
				territory.set_interaction_enabled(false)
	
	open_deploy_popup(territory_name)
