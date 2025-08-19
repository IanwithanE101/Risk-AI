extends Node

var socket := StreamPeerTCP.new()
var connected := false
var territories := {}

# UI element references
var end_button: Button
var deploy_controls_script: Node
var attack_controls_script: Node
var fortify_controls_script: Node

# Game state
var current_phase := "deploy"
var current_player := 1
var is_user_turn := false

func _ready():
	# Cache territories
	var territories_container = get_node_or_null("Territories")
	if territories_container:
		for territory in territories_container.get_children():
			if territory is Area2D:
				territories[territory.name] = territory
				print("📍 Cached territory:", territory.name)
	
	# Get reference to End Button in GeneralUI
	end_button = get_node_or_null("GeneralUI/End_Button")
	if not end_button:
		print("❌ CLIENT: End_Button not found at GeneralUI/End_Button!")
		# Try alternative paths
		end_button = get_node_or_null("End_Button")  # Fallback to old location
		if end_button:
			print("✅ CLIENT: Found End_Button at fallback location")
	else:
		print("✅ CLIENT: Found End_Button at GeneralUI/End_Button")
	
	if end_button:
		# Attach the button script if not already attached
		if not end_button.has_method("set_phase"):
			end_button.set_script(preload("res://Scripts/end_button.gd"))
		
		# Connect to button's signal
		end_button.end_action_pressed.connect(_on_end_phase)
		
		# Start with button disabled
		end_button.set_enabled(false)
		print("✅ CLIENT: End button configured successfully")
	else:
		print("❌ CLIENT: Could not find End_Button anywhere!")
	
	# Get references to the central controls node
	var controls_node = get_node_or_null("Controls")
	if controls_node:
		print("🔍 CLIENT: Found Controls node")
		deploy_controls_script = controls_node
		attack_controls_script = controls_node
		fortify_controls_script = controls_node
	else:
		print("❌ CLIENT: Controls node not found!")
		deploy_controls_script = null
		attack_controls_script = null
		fortify_controls_script = null
	
	# Connect to server
	var err = socket.connect_to_host("127.0.0.1", 9999)
	print("🧪 connect_to_host() returned:", err)

func _on_end_phase(phase: String):
	print("🎮 Ending phase:", phase)
	
	var command = {
		"type": "end_phase",
		"player": current_player,
		"phase": phase
	}
	
	send_command(command)
	
	# Disable button after sending
	if end_button:
		end_button.set_enabled(false)

func send_command(command: Dictionary):
	if connected:
		var message = JSON.stringify(command) + "\n"
		socket.put_utf8_string(message)
		print("📤 Sent command:", command)
	else:
		print("❌ Not connected, can't send command")

func request_troop_income(player_id: int):
	"""Requests troop income from server."""
	print("🔍 CLIENT: Requesting troop income for Player ", player_id)
	var command = {
		"type": "request_troop_income",
		"player_id": player_id
	}
	send_command(command)

func send_deploy_troops(player_id: int, territory_name: String, troops: int):
	"""Sends deploy troops command to server."""
	print("🔍 CLIENT: Sending deploy troops - Player ", player_id, " Territory: ", territory_name, " Troops: ", troops)
	var command = {
		"type": "deploy_troops",
		"player_id": player_id,
		"territory": territory_name,
		"troops": troops
	}
	send_command(command)

func _process(_delta):
	socket.poll()
	
	if not connected:
		var status = socket.get_status()
		
		if status == StreamPeerTCP.STATUS_CONNECTED:
			connected = true
			print("✅ Connected to Risk server!")
			if end_button:
				end_button.set_enabled(true)
		elif status == StreamPeerTCP.STATUS_ERROR:
			print("❌ Connection failed!")
			return
		elif status == StreamPeerTCP.STATUS_CONNECTING:
			return
		else:
			return
	
	# Read incoming data - DECLARE EACH VARIABLE ONLY ONCE
	var available := socket.get_available_bytes()
	if available == 0:
		return
	
	var message := socket.get_utf8_string(available).strip_edges()
	if message == "":
		return
	
	# Rest of your message processing...
	for line in message.split("\n"):
		if line.strip_edges() == "":
			continue
		
		var data = JSON.parse_string(line)
		if data == null or typeof(data) != TYPE_DICTIONARY:
			print("❌ Bad JSON:", line)
			continue
		
		# Handle different message types
		match data.get("type"):
			"player_cards_response":
				_handle_player_cards_response(data)
			"territory_update":
				_handle_territory_update(data)
			"phase_update":
				_handle_phase_update(data)
			"turn_update":
				_handle_turn_update(data)
			"troop_income_response":
				_handle_troop_income_response(data)
			"deploy_response":
				_handle_deploy_response(data)

func _handle_territory_update(payload):
	var territory_name = payload.get("name", "")
	var owner = payload.get("owner", null)
	var troops = payload.get("troops", -1)
	
	print("🔍 CLIENT: Territory Update - Name: ", territory_name, " Owner: ", owner, " Troops: ", troops)
	
	if territory_name in territories:
		print("🔍 CLIENT: Found territory ", territory_name, " in cache, updating...")
		territories[territory_name].update_owner(owner, troops)
		# Also update the territory's phase info
		print("🔍 CLIENT: Updating game state for ", territory_name, " - Phase: ", current_phase, " Player: ", current_player)
		territories[territory_name].update_game_state(current_phase, current_player)
	else:
		print("❌ CLIENT: Territory not found in cache: ", territory_name)
		print("🔍 CLIENT: Available territories: ", territories.keys())

func _handle_phase_update(payload):
	current_phase = payload.get("phase", "")
	var player = payload.get("player", 0)
	is_user_turn = payload.get("is_user", false)
	
	print("🔍 CLIENT: Phase Update - Phase: ", current_phase, " Player: ", player, " Is User: ", is_user_turn)
	
	# Update button to show current phase
	if end_button:
		end_button.set_phase(current_phase)
	
	# Update all territories with new phase info
	for territory in territories.values():
		territory.update_game_state(current_phase, current_player)
	
	# If it's a user turn, activate the appropriate controls
	if is_user_turn:
		print("🔍 CLIENT: This is a user turn, activating controls...")
		match current_phase:
			"deploy":
				print("🔍 CLIENT: Checking for deploy controls script...")
				if deploy_controls_script:
					print("🔍 CLIENT: Deploy controls script found, checking for activate_phase method...")
					if deploy_controls_script.has_method("activate_phase"):
						print("🔍 CLIENT: Calling activate_phase on deploy controls")
						deploy_controls_script.activate_phase(current_phase, current_player)
						print("🎮 Activated deploy controls")
					else:
						print("❌ CLIENT: Deploy controls script missing activate_phase method!")
				else:
					print("❌ CLIENT: Deploy controls script not found!")
			"attack":
				print("🔍 CLIENT: Checking for attack controls script...")
				if attack_controls_script and attack_controls_script.has_method("activate_phase"):
					attack_controls_script.activate_phase(current_phase, current_player)
					print("🎮 Activated attack controls")
				else:
					print("❌ CLIENT: Attack controls script not found or missing method!")
			"fortify":
				print("🔍 CLIENT: Checking for fortify controls script...")
				if fortify_controls_script and fortify_controls_script.has_method("activate_phase"):
					fortify_controls_script.activate_phase(current_phase, current_player)
					print("🎮 Activated fortify controls")
				else:
					print("❌ CLIENT: Fortify controls script not found or missing method!")
	else:
		print("🔍 CLIENT: This is an AI turn, not activating controls")
	
	# Re-enable button for next action
	if end_button:
		end_button.set_enabled(true)

func _handle_turn_update(payload):
	current_player = payload.get("current_player", 0)
	print("🎮 New turn: Player", current_player)

func _handle_troop_income_response(payload):
	var player_id = payload.get("player_id", 0)
	var troop_income = payload.get("troop_income", 0)
	
	print("🔍 CLIENT: Received troop income response - Player ", player_id, " gets ", troop_income, " troops")
	
	# Pass this to deploy controls script
	if deploy_controls_script and deploy_controls_script.has_method("set_troops_to_deploy"):
		print("🔍 CLIENT: Calling set_troops_to_deploy on deploy controls")
		deploy_controls_script.set_troops_to_deploy(troop_income)
	else:
		print("❌ CLIENT: Deploy controls script not found or method missing!")

var waiting_general_ui: Node = null

func request_current_player_cards(requesting_ui: Node):
	"""Request current player's cards from server (server determines current player)"""
	waiting_general_ui = requesting_ui
	
	var command = {
		"type": "request_current_player_cards"
	}
	
	send_command(command)
	print("RiskClient: Requested cards for current player (server will determine who)")

func _handle_player_cards_response(payload):
	"""Handle receiving player cards from server"""
	var player_id = payload.get("player_id", 0)
	var cards_data = payload.get("cards", [])
	
	print("RiskClient: Received ", cards_data.size(), " cards for current player ", player_id)
	
	# Forward to waiting GeneralUI
	if waiting_general_ui and waiting_general_ui.has_method("receive_player_cards"):
		waiting_general_ui.receive_player_cards(cards_data)
		waiting_general_ui = null
	else:
		print("ERROR: No GeneralUI waiting for cards or missing method!")

func _handle_deploy_response(payload):
	var success = payload.get("success", false)
	var player_id = payload.get("player_id", 0)
	var territory = payload.get("territory", "")
	var troops = payload.get("troops", 0)
	
	print("🔍 CLIENT: Received deploy response - Success: ", success, " Player: ", player_id, " Territory: ", territory, " Troops: ", troops)
	
	# Pass response to deploy controls script
	if deploy_controls_script and deploy_controls_script.has_method("handle_deploy_response"):
		print("🔍 CLIENT: Calling handle_deploy_response on deploy controls")
		deploy_controls_script.handle_deploy_response(success, territory, troops)
	else:
		print("❌ CLIENT: Deploy controls script not found or method missing!")
