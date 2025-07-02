extends Node

var socket := StreamPeerTCP.new()
var connected := false

func _ready():
	var err = socket.connect_to_host("127.0.0.1", 9999)
	if err != OK:
		print("Connection failed:", err)
	else:
		connected = true
		print("Connected to Risk server")

func _process(_delta):
	if connected and socket.get_available_bytes() > 0:
		var text = socket.get_utf8_string(socket.get_available_bytes())
		for line in text.split("\n"):
			if line.strip_edges() == "":
				continue
			var data = JSON.parse_string(line)
			if typeof(data) == TYPE_DICTIONARY:
				_handle_board_update(data)

func _handle_board_update(payload):
	if payload.has("typ`") and payload["type"] == "board":
		var board = payload["data"]
		for territory_name in board.keys():
			var info = board[territory_name]
			var territory = get_node_or_null("/root/Main/" + territory_name)
			if territory and info.has("owner"):
				territory.update_owner(info["owner"], info.get("troops", 0))
