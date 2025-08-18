# GeneralUI.gd - Main UI controller script
extends Node2D

# Card scene path
const CARD_SCENE_PATH = "res://Scenes/Card.tscn"
const MAX_CARDS = 5
const CARD_WIDTH = 250
const CARD_SPACING = 25
const CONTAINER_WIDTH = 1350

# UI References
@onready var cards_button: Button = $Cards
@onready var cards_popup: Window = $Cards/CardsPopup
@onready var card_container: HBoxContainer = $Cards/CardsPopup/VBoxContainer/HBoxContainer

# Card references - dynamically created
var cards: Array[Node] = []
var card_scene: PackedScene

func _ready():
	print("=== GeneralUI _ready() called ===")
	print("GeneralUI: My name is: ", name)
	if get_parent():
		print("GeneralUI: My parent is: ", get_parent().name)
	else:
		print("GeneralUI: No parent")
	print("GeneralUI: My path is: ", get_path())
	
	# Load the card scene
	card_scene = load(CARD_SCENE_PATH)
	if not card_scene:
		print("ERROR: Could not load Card scene from ", CARD_SCENE_PATH)
		return
	else:
		print("GeneralUI: Card scene loaded successfully")
	
	# Connect cards button to open popup
	if cards_button:
		cards_button.pressed.connect(_on_cards_button_pressed)
		print("GeneralUI: Cards button connected")
	else:
		print("ERROR: cards_button is null! @onready failed")
		# Try to find it manually
		cards_button = get_node_or_null("Cards")
		if cards_button:
			print("GeneralUI: Found Cards button manually")
			cards_button.pressed.connect(_on_cards_button_pressed)
	
	# Set up HBoxContainer spacing and alignment
	if card_container:
		card_container.add_theme_constant_override("separation", CARD_SPACING)
		card_container.alignment = BoxContainer.ALIGNMENT_CENTER
		print("GeneralUI: Set HBoxContainer spacing to ", CARD_SPACING, " pixels and alignment to CENTER")
	else:
		print("ERROR: card_container is null! @onready failed")
		# Try to find it manually
		card_container = get_node_or_null("Cards/CardsPopup/VBoxContainer/HBoxContainer")
		if card_container:
			print("GeneralUI: Found HBoxContainer manually")
			card_container.add_theme_constant_override("separation", CARD_SPACING)
			card_container.alignment = BoxContainer.ALIGNMENT_CENTER
	
	# Initialize with example cards
	call_deferred("create_example_cards")
	print("=== GeneralUI _ready() complete ===")

func _on_cards_button_pressed():
	"""Open the cards popup window and request current player's cards"""
	if cards_popup:
		cards_popup.visible = true
		print("GeneralUI: Cards popup opened")
		
		# Clear existing cards before requesting new ones
		clear_all_cards()
		
		# Request current player's cards from RiskClient
		request_player_cards()

func request_player_cards():
	"""Request current player's cards from RiskClient"""
	# Try multiple possible paths to find RiskClient
	var risk_client = get_node_or_null("../RiskClient")  # If GeneralUI is sibling to RiskClient
	if not risk_client:
		risk_client = get_node_or_null("/root/Main/RiskClient")  # If in Main scene
	if not risk_client:
		risk_client = get_parent()  # If RiskClient is parent
		if not risk_client.has_method("request_current_player_cards"):
			risk_client = null
	if not risk_client:
		# Try to find any node with the method
		risk_client = get_tree().get_first_node_in_group("risk_client")
	
	if risk_client and risk_client.has_method("request_current_player_cards"):
		print("GeneralUI: Found RiskClient, requesting cards...")
		risk_client.request_current_player_cards(self)
	else:
		print("ERROR: Could not find RiskClient! Available nodes:")
		if get_parent():
			print("  Parent: ", get_parent().name)
			print("  Siblings: ", get_parent().get_children().map(func(n): return n.name))
		else:
			print("  Parent: None")
			print("  Siblings: None")
		# Fallback to example cards
		create_example_cards()

func receive_player_cards(cards_data: Array):
	"""Called by RiskClient when card data is received"""
	print("GeneralUI: Received ", cards_data.size(), " cards from server")
	
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
	
	print("GeneralUI: Successfully created ", cards.size(), " cards from server data")

func create_card(territory_name: String, card_type: String) -> Node:
	"""Create a new card and add it to the container"""
	if cards.size() >= MAX_CARDS:
		print("WARNING: Cannot create more than ", MAX_CARDS, " cards! Current count: ", cards.size())
		print("WARNING: Attempted to create card '", territory_name, "' of type '", card_type, "' but limit exceeded")
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
		new_card.set_card_size(Vector2(CARD_WIDTH, 350))  # Set proper size
	new_card.custom_minimum_size = Vector2(CARD_WIDTH, 350)  # Prevent shrinking
	new_card.size = Vector2(CARD_WIDTH, 350)  # Force size
	
	# Prevent HBoxContainer from shrinking this card
	new_card.set_h_size_flags(Control.SIZE_SHRINK_CENTER)
	new_card.set_v_size_flags(Control.SIZE_SHRINK_CENTER)
	
	# Set up the card
	if new_card.has_method("setup_card"):
		new_card.setup_card(territory_name, card_type)
	if new_card.has_method("set_card_visible"):
		new_card.set_card_visible()
	
	print("GeneralUI: Created card ", cards.size(), "/", MAX_CARDS, " - '", territory_name, "' (", card_type, ")")
	print("GeneralUI: Container now has ", card_container.get_child_count(), " total children")
	
	# Check spacing calculation
	var total_width_needed = (cards.size() * CARD_WIDTH) + ((cards.size() - 1) * CARD_SPACING)
	print("GeneralUI: Total width needed: ", total_width_needed, "/", CONTAINER_WIDTH, " pixels")
	
	return new_card

func create_example_cards():
	"""Create example cards for testing"""
	print("GeneralUI: Creating example cards...")
	
	var example_data = [
		{"name": "Alaska", "type": "Infantry"},
		{"name": "Brazil", "type": "Cavalry"}, 
		{"name": "Egypt", "type": "Artillery"},
		{"name": "China", "type": "Wildcard"}
	]
	
	for data in example_data:
		create_card(data.name, data.type)
	
	print("GeneralUI: Finished creating ", cards.size(), " example cards")

func clear_all_cards():
	"""Remove all cards from container"""
	print("GeneralUI: Clearing all cards...")
	
	for card in cards:
		if card and is_instance_valid(card):
			card.queue_free()
	
	cards.clear()
	print("GeneralUI: All cards cleared")

func on_card_clicked(card: Node):
	"""Called when any card is clicked"""
	var card_name = card.get_territory_name() if card.has_method("get_territory_name") else "Unknown"
	var card_type = card.get_card_type() if card.has_method("get_card_type") else "Unknown"
	print("GeneralUI: Card clicked - ", card_name, " (", card_type, ")")
	
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
	print("GeneralUI: Card selection updated for ", card_name)

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

# Utility methods for managing cards
func get_card(index: int) -> Card:
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
