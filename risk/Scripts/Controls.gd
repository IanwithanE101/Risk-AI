extends Node

# ================================================================
# UI REFERENCES - CONTROLS SYSTEM
# ================================================================
var deploy_controls: Node
var attack_controls: Node  
var fortify_controls: Node
var troop_deploy_popup: Window  # Changed from PopupPanel to Window (since it has border with X)
var feedback_label: Label
var troop_selection_label: Label
var troop_slider: HSlider
var confirm_button: Button
var cancel_button: Button

# ================================================================
# UI REFERENCES - CARDS SYSTEM (FROM GENERALUI)
# ================================================================
# Card scene path
const CARD_SCENE_PATH = "res://Scenes/Card.tscn"
const MAX_CARDS = 5
const CARD_WIDTH = 250
const CARD_SPACING = 25
const CONTAINER_WIDTH = 1350

# Cards UI References - NEW PATHS
var cards_button: Button
var cards_popup: Window
var card_container: HBoxContainer

# Card management
var cards: Array[Node] = []
var card_scene: PackedScene

# ================================================================
# GAME STATE
# ================================================================
var current_phase := ""
var current_player := 0
var troops_to_deploy := 0
var selected_territory := ""
var risk_client: Node

# Attack phase specific
var attack_arrow_line: Line2D = null
var is_attacking := false
var attack_from_position := Vector2.ZERO
var attack_from_territory := ""

func _ready():
	print("🔍 CONTROLS: _ready() called")
	print("🔍 CONTROLS: My parent is: ", get_parent().name)
	# Create attack arrow line
	attack_arrow_line = Line2D.new()
	attack_arrow_line.width = 3.0
	attack_arrow_line.default_color = Color(1.0, 1.0, 0.0, 0.7)  # Yellow semi-transparent
	attack_arrow_line.add_point(Vector2.ZERO)
	attack_arrow_line.add_point(Vector2.ZERO)
	attack_arrow_line.visible = false
	add_child(attack_arrow_line)
	print("Crafted the arrow.")
	# ================================================================
	# FIND DEPLOY/ATTACK/FORTIFY CONTROLS
	# ================================================================
	deploy_controls = get_node_or_null("deploy_controls")
	attack_controls = get_node_or_null("attack_controls") 
	fortify_controls = get_node_or_null("fortify_controls")
	
	# Find UI elements within deploy_controls - FIXED PATHS
	if deploy_controls:
		print("✅ CONTROLS: Found deploy_controls")
		troop_deploy_popup = deploy_controls.get_node_or_null("TroopDeployPopup")
		feedback_label = deploy_controls.get_node_or_null("Feedback")
		troop_selection_label = deploy_controls.get_node_or_null("TroopDeployPopup/VBoxContainer/troop_selection_label")
		troop_slider = deploy_controls.get_node_or_null("TroopDeployPopup/VBoxContainer/troop_slider")
		confirm_button = deploy_controls.get_node_or_null("TroopDeployPopup/VBoxContainer/Confirm")
		cancel_button = deploy_controls.get_node_or_null("TroopDeployPopup/VBoxContainer/Cancel")
		
		# Configure the window popup behavior
		if troop_deploy_popup:
			troop_deploy_popup.set_flag(Window.FLAG_POPUP, false)
			troop_deploy_popup.unresizable = true
			troop_deploy_popup.always_on_top = true
			
			# Connect to the BUILT-IN X button signal
			if not troop_deploy_popup.close_requested.is_connected(_on_popup_x_clicked):
				troop_deploy_popup.close_requested.connect(_on_popup_x_clicked)
				print("✅ CONTROLS: Connected built-in X button signal")
	else:
		print("❌ CONTROLS: deploy_controls child not found!")
	
	# ================================================================
	# FIND CARDS SYSTEM (NEW PATHS)
	# ================================================================
	cards_button = get_node_or_null("GeneralUI/Cards")
	cards_popup = get_node_or_null("GeneralUI/Cards/CardsPopup") 
	card_container = get_node_or_null("GeneralUI/Cards/CardsPopup/VBoxContainer/HBoxContainer")
	
	print("=== CARDS SYSTEM SETUP ===")
	print("Cards button found: ", cards_button != null)
	print("Cards popup found: ", cards_popup != null)
	print("Card container found: ", card_container != null)
	
	# Load the card scene
	card_scene = load(CARD_SCENE_PATH)
	if not card_scene:
		print("ERROR: Could not load Card scene from ", CARD_SCENE_PATH)
	else:
		print("✅ CONTROLS: Card scene loaded successfully")
	
	# Connect cards button to open popup
	if cards_button:
		cards_button.pressed.connect(_on_cards_button_pressed)
		print("✅ CONTROLS: Cards button connected")
	else:
		print("ERROR: cards_button not found at GeneralUI/Cards!")
	
	# Configure the cards popup window behavior
	if cards_popup:
		cards_popup.set_flag(Window.FLAG_POPUP, false)
		cards_popup.unresizable = true
		cards_popup.always_on_top = true
		
		# Connect to the BUILT-IN X button signal
		if not cards_popup.close_requested.is_connected(_on_cards_popup_x_clicked):
			cards_popup.close_requested.connect(_on_cards_popup_x_clicked)
			print("✅ CONTROLS: Connected built-in X button signal for cards popup")
	
	# Set up HBoxContainer spacing and alignment
	if card_container:
		card_container.add_theme_constant_override("separation", CARD_SPACING)
		card_container.alignment = BoxContainer.ALIGNMENT_CENTER
		print("✅ CONTROLS: Set HBoxContainer spacing to ", CARD_SPACING, " pixels and alignment to CENTER")
	else:
		print("ERROR: card_container not found!")
	
	# ================================================================
	# RISKCLIENT REFERENCE
	# ================================================================
	risk_client = get_parent()  # Controls is child of Main, which has RiskClient.gd attached
	if risk_client and risk_client.has_method("request_troop_income"):
		print("✅ CONTROLS: Found RiskClient as parent")
	else:
		print("❌ CONTROLS: Could not find RiskClient methods in parent!")
	
	# ================================================================
	# CONNECT DEPLOY POPUP BUTTONS
	# ================================================================
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
	
	# Start with all controls hidden (but NOT GeneralUI - it stays visible)
	hide_all_controls()

# ================================================================
# PHASE MANAGEMENT - CRITICAL METHODS RISKCLIENT EXPECTS
# ================================================================

func hide_all_controls():
	"""Hides all phase controls but NOT GeneralUI elements."""
	print("🔍 CONTROLS: Hiding phase controls (keeping GeneralUI visible)")
	
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
		troop_deploy_popup.hide()  # Use hide() for Window nodes
		print("🔍 CONTROLS: Hidden troop_deploy_popup")
	else:
		print("❌ CONTROLS: troop_deploy_popup node not found!")
	
	# NOTE: GeneralUI (cards button, end button) stays visible always

# ================================================================
# CRITICAL METHOD: RISKCLIENT CALLS THIS
# ================================================================
func activate_phase(phase: String, player: int):
	"""Activates controls for the given phase - REQUIRED BY RISKCLIENT."""
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
		troop_deploy_popup.hide()
	
	# Request troop income from server
	if risk_client and risk_client.has_method("request_troop_income"):
		print("🔍 CONTROLS: Requesting troop income from RiskClient")
		risk_client.request_troop_income(current_player)
	else:
		print("❌ CONTROLS: Cannot request troop income - RiskClient method missing")
	
	# Update feedback label
	update_feedback_label()

func activate_fortify_phase():
	"""Activates fortify phase controls (placeholder)."""
	print("🏰 CONTROLS: Activating fortify phase (not implemented)")
	if fortify_controls:
		fortify_controls.visible = true

# ================================================================
# CRITICAL METHOD: RISKCLIENT CALLS THIS
# ================================================================
func set_troops_to_deploy(amount: int):
	"""Sets the number of troops available to deploy - REQUIRED BY RISKCLIENT."""
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
	# End button is now in GeneralUI
	var end_button = get_node_or_null("GeneralUI/End_Button")
	if end_button and end_button.has_method("set_enabled"):
		if troops_to_deploy > 0:
			end_button.set_enabled(false)  # Disable if troops remain
			print("🚫 CONTROLS: End phase button disabled - troops remaining:", troops_to_deploy)
		else:
			end_button.set_enabled(true)   # Enable if no troops remain
			print("✅ CONTROLS: End phase button enabled - no troops remaining")
	else:
		print("❌ CONTROLS: Could not find end button at GeneralUI/End_Button")

# ================================================================
# DEPLOY POPUP MANAGEMENT
# ================================================================

func open_deploy_popup(territory_name: String):
	"""Opens the troop deployment popup for the selected territory."""
	if troops_to_deploy <= 0:
		print("❌ CONTROLS: No troops available to deploy!")
		return
	
	selected_territory = territory_name
	print("🎯 CONTROLS: Opening deploy popup for territory:", territory_name)
	
	if troop_deploy_popup:
		troop_deploy_popup.popup_centered()
		
		# Configure slider
		if troop_slider:
			troop_slider.min_value = 1
			troop_slider.max_value = troops_to_deploy
			troop_slider.step = 1
			troop_slider.value = 1
			
			print("✅ CONTROLS: Slider configured - Range: 1 to", troops_to_deploy)
			_on_slider_changed(1)
		else:
			print("❌ CONTROLS: troop_slider not found!")

func close_deploy_popup():
	"""Closes the deploy popup and cleans up connections."""
	if troop_deploy_popup:
		troop_deploy_popup.hide()
	
	selected_territory = ""
	
	# Re-enable territory interactions
	enable_territory_interactions()

# ================================================================
# CRITICAL METHOD: RISKCLIENT CALLS THIS
# ================================================================
func handle_deploy_response(success: bool, territory: String, troops: int):
	"""Handles response from server about deployment - REQUIRED BY RISKCLIENT."""
	if success:
		print("✅ CONTROLS: Deploy successful:", troops, "troops to", territory)
		# Subtract from available troops
		troops_to_deploy -= troops
		update_feedback_label()
		check_end_phase_button()
	else:
		print("❌ CONTROLS: Deploy failed for territory:", territory)

# ================================================================
# TERRITORY INTERACTION
# ================================================================

func territory_clicked(territory_name: String, territory_owner: int):
	"""Called when a territory is clicked during deploy phase."""
	if current_phase != "deploy":
		return
	
	if territory_owner != current_player:
		print("❌ CONTROLS: Can only deploy to your own territories!")
		return
	
	# Disable territory interactions while popup is open
	disable_territory_interactions()
	
	open_deploy_popup(territory_name)

func disable_territory_interactions():
	"""Disable territory interactions while popup is open"""
	var territories_node = get_parent().get_node_or_null("Territories")
	if territories_node:
		for territory in territories_node.get_children():
			if territory.has_method("set_interaction_enabled"):
				territory.set_interaction_enabled(false)
		print("✅ CONTROLS: Disabled territory interactions")
	else:
		print("ERROR: Could not find Territories node to disable interactions")

func enable_territory_interactions():
	"""Re-enable territory interactions when popup closes"""
	var territories_node = get_parent().get_node_or_null("Territories")
	if territories_node:
		for territory in territories_node.get_children():
			if territory.has_method("set_interaction_enabled"):
				territory.set_interaction_enabled(true)
		print("✅ CONTROLS: Re-enabled territory interactions")
	else:
		print("ERROR: Could not find Territories node to enable interactions")

# ================================================================
# CARDS POPUP MANAGEMENT (FROM GENERALUI)
# ================================================================

func _on_cards_button_pressed():
	"""Open the cards popup window and request current player's cards"""
	if cards_popup:
		cards_popup.popup_centered()
		print("✅ CONTROLS: Cards popup opened")
		
		# Disable territory interactions while popup is open
		disable_territory_interactions()
		
		# Clear existing cards before requesting new ones
		clear_all_cards()
		
		# Request current player's cards from RiskClient
		request_player_cards()

func _on_cards_popup_x_clicked():
	"""Called when user clicks the built-in X button on cards popup"""
	print("❌ CONTROLS: User clicked X button on cards popup - closing")
	close_cards_popup()

func close_cards_popup():
	"""Closes the cards popup window"""
	if cards_popup:
		cards_popup.hide()
		print("✅ CONTROLS: Cards popup closed")
	
	# Re-enable territory interactions
	enable_territory_interactions()

# ================================================================
# CARDS DATA MANAGEMENT (FROM GENERALUI)
# ================================================================

func request_player_cards():
	"""Request current player's cards from RiskClient"""
	if risk_client and risk_client.has_method("request_current_player_cards"):
		print("✅ CONTROLS: Found RiskClient, requesting cards...")
		risk_client.request_current_player_cards(self)
	else:
		print("ERROR: Could not find RiskClient method for cards!")

# ================================================================
# CRITICAL METHOD: RISKCLIENT CALLS THIS FOR CARDS
# ================================================================
func receive_player_cards(cards_data: Array):
	"""Called by RiskClient when card data is received - REQUIRED BY RISKCLIENT."""
	print("✅ CONTROLS: Received ", cards_data.size(), " cards from server")
	
	# Clear existing cards
	clear_all_cards()
	
	# Check for more than 5 cards
	if cards_data.size() > MAX_CARDS:
		print("WARNING: Player has ", cards_data.size(), " cards, but maximum displayable is ", MAX_CARDS)
		print("WARNING: Only showing first ", MAX_CARDS, " cards")
		
		# Truncate to MAX_CARDS
		var truncated_data = []
		for i in range(MAX_CARDS):
			truncated_data.append(cards_data[i])
		cards_data = truncated_data
	
	# Create cards from received data
	for card_data in cards_data:
		if card_data.has("name") and card_data.has("type"):
			create_card(card_data.name, card_data.type)
		else:
			print("ERROR: Invalid card data format: ", card_data)
	
	print("✅ CONTROLS: Successfully created ", cards.size(), " cards from server data")

# ================================================================
# CARD CREATION AND MANAGEMENT (FROM GENERALUI)
# ================================================================

func create_card(territory_name: String, card_type: String) -> Node:
	"""Create a new card and add it to the container"""
	if cards.size() >= MAX_CARDS:
		print("WARNING: Cannot create more than ", MAX_CARDS, " cards! Current count: ", cards.size())
		return null
	
	if not card_scene:
		print("ERROR: Card scene not loaded!")
		return null
	
	if not card_container:
		print("ERROR: Card container not found!")
		return null
	
	# Create new card instance
	var new_card = card_scene.instantiate()
	if not new_card:
		print("ERROR: Failed to instantiate card scene!")
		return null
	
	# Add to container
	card_container.add_child(new_card)
	cards.append(new_card)
	
	# Set proper card size and prevent shrinking
	if new_card.has_method("set_card_size"):
		new_card.set_card_size(Vector2(CARD_WIDTH, 350))
	new_card.custom_minimum_size = Vector2(CARD_WIDTH, 350)
	new_card.size = Vector2(CARD_WIDTH, 350)
	
	# Prevent HBoxContainer from shrinking this card
	new_card.set_h_size_flags(Control.SIZE_SHRINK_CENTER)
	new_card.set_v_size_flags(Control.SIZE_SHRINK_CENTER)
	
	# Set up the card
	if new_card.has_method("setup_card"):
		new_card.setup_card(territory_name, card_type)
	if new_card.has_method("set_card_visible"):
		new_card.set_card_visible()
	
	print("✅ CONTROLS: Created card ", cards.size(), "/", MAX_CARDS, " - '", territory_name, "' (", card_type, ")")
	
	return new_card

func clear_all_cards():
	"""Remove all cards from container"""
	print("✅ CONTROLS: Clearing all cards...")
	
	for card in cards:
		if card and is_instance_valid(card):
			card.queue_free()
	
	cards.clear()
	print("✅ CONTROLS: All cards cleared")

# ================================================================
# CARD INTERACTION (FROM GENERALUI)
# ================================================================

func on_card_clicked(card: Node):
	"""Called when any card is clicked"""
	var card_name = card.get_territory_name() if card.has_method("get_territory_name") else "Unknown"
	var card_type = card.get_card_type() if card.has_method("get_card_type") else "Unknown"
	print("✅ CONTROLS: Card clicked - ", card_name, " (", card_type, ")")
	
	# Handle card selection logic
	handle_card_selection(card)

func handle_card_selection(clicked_card: Node):
	"""Manage card selection - only one card can be selected at a time"""
	# First, deselect all other cards
	for card in cards:
		if card and card != clicked_card and card.has_method("set_clicked_state"):
			card.set_clicked_state(false)
	
	# The clicked card toggles its own state automatically
	var card_name = clicked_card.get_territory_name() if clicked_card.has_method("get_territory_name") else "Unknown"
	print("✅ CONTROLS: Card selection updated for ", card_name)

func get_selected_card() -> Node:
	"""Get the currently selected card"""
	for card in cards:
		if card and card.has_method("is_clicked") and card.is_clicked:
			return card
	return null

func clear_all_selections():
	"""Deselect all cards"""
	for card in cards:
		if card:
			card.set_clicked_state(false)

# ================================================================
# CARD UTILITY METHODS (FROM GENERALUI)
# ================================================================

func get_card(index: int) -> Node:  # Changed from Card to Node
	"""Get a specific card by index (0-4)"""
	if index >= 0 and index < cards.size():
		return cards[index]
	return null

func update_card(index: int, name: String, type: String):
	"""Update a specific card"""
	var card = get_card(index)
	if card:
		card.setup_card(name, type)
		card.set_card_visible()

func hide_card(index: int):
	"""Hide a specific card"""
	var card = get_card(index)
	if card:
		card.set_card_invisible()

func show_all_cards():
	"""Make all cards visible"""
	for card in cards:
		if card:
			card.set_card_visible()

func hide_all_cards():
	"""Hide all cards"""
	for card in cards:
		if card:
			card.set_card_invisible()

# ================================================================
# DEPLOY POPUP SIGNAL HANDLERS
# ================================================================

func _on_slider_changed(value: float):
	"""Updates troop selection label when slider changes."""
	var troops_selected = int(value)
	
	print("🎯 CONTROLS: Slider value:", troops_selected)
	
	# Update the label
	if troop_selection_label:
		troop_selection_label.text = str(troops_selected)
		print("✅ CONTROLS: Updated label to:", troops_selected)
	else:
		print("❌ CONTROLS: troop_selection_label not found!")

func _on_confirm_deploy():
	"""Confirms troop deployment with better error handling."""
	if not selected_territory:
		print("❌ CONTROLS: No territory selected!")
		return
	
	if not troop_slider or not is_instance_valid(troop_slider):
		print("❌ CONTROLS: Slider not available!")
		return
	
	var troops_selected = int(troop_slider.value)
	
	# Validate selection
	if troops_selected < 1 or troops_selected > troops_to_deploy:
		print("❌ CONTROLS: Invalid troop count:", troops_selected, "Range: 1-", troops_to_deploy)
		return
	
	print("✅ CONTROLS: Confirming deploy:", troops_selected, "troops to", selected_territory)
	
	# Send deploy command to server
	if risk_client and risk_client.has_method("send_deploy_troops"):
		risk_client.send_deploy_troops(current_player, selected_territory, troops_selected)
	else:
		print("❌ CONTROLS: Cannot send deploy command - RiskClient method missing!")
	
	# Close popup
	close_deploy_popup()

func _on_cancel_deploy():
	"""Cancels troop deployment."""
	print("❌ CONTROLS: Cancelled deploy")
	close_deploy_popup()

func _on_popup_x_clicked():
	"""Called when user clicks the built-in X button on window border"""
	print("❌ CONTROLS: User clicked built-in X button - cancelling deploy")
	_on_cancel_deploy()  # Same cleanup as cancel button

func activate_attack_phase():
	"""Activates attack phase controls."""
	print("⚔️ CONTROLS: Activating attack phase")
	
	if attack_controls:
		attack_controls.visible = true
	
	# Enable territory interactions for attack selection
	enable_territory_interactions()

func start_attack_selection(territory_name: String, from_position: Vector2):
	"""Called when user starts selecting an attack (mouse down on valid attacker)."""
	print("⚔️ CONTROLS: Starting attack from", territory_name)
	is_attacking = true
	attack_from_territory = territory_name
	attack_from_position = from_position
	
	# Show and position arrow
	if attack_arrow_line:
		attack_arrow_line.visible = true
		attack_arrow_line.set_point_position(0, from_position)
		attack_arrow_line.set_point_position(1, from_position)

func execute_attack(from_territory: String, to_territory: String):
	"""Executes an attack between two territories."""
	print("🎯 CONTROLS: Executing attack from", from_territory, "to", to_territory)
	
	# Send attack command to server
	if risk_client and risk_client.has_method("send_attack"):
		risk_client.send_attack(current_player, from_territory, to_territory)
	else:
		print("❌ CONTROLS: Cannot send attack command - RiskClient method missing!")
	
	# Hide arrow
	end_attack_selection()

func end_attack_selection():
	"""Cleans up attack selection state."""
	is_attacking = false
	attack_from_territory = ""
	attack_from_position = Vector2.ZERO
	
	if attack_arrow_line:
		attack_arrow_line.visible = false

# Add this to handle arrow following mouse:
func _process(_delta):
	"""Updates attack arrow to follow mouse."""
	if is_attacking and attack_arrow_line and attack_arrow_line.visible:
		var mouse_pos = get_global_mouse_position()
		attack_arrow_line.set_point_position(1, mouse_pos)

# Also add this to properly handle when mouse is released outside territories:
func _input(event):
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT and not event.pressed:
			if is_attacking:
				# Mouse released but not on a valid target
				print("❌ CONTROLS: Attack cancelled")
				end_attack_selection()
				# Clear all territory states
				var territories = get_parent().get_node_or_null("Territories")
				if territories:
					for territory in territories.get_children():
						if territory.has_method("clear_attack_state"):
							territory.clear_attack_state()
