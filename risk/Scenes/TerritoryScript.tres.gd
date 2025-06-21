extends Area2D

@export var texture:Texture2D         # assign PNG per territory
@export var dim_amount := 0.8
@export var colours := [
	Color.RED, Color.BLUE,
	Color.GREEN, Color.YELLOW,
	Color.WHITE          # default off-white
]
@export var start_colour_index := 4   # start on white by default

var idx := 0
var hovered := false
@onready var sprite := $Sprite2D

func _ready():
	idx = start_colour_index
	sprite.texture = texture
	_apply_colour()
	connect("mouse_entered", _on_enter)
	connect("mouse_exited", _on_exit)
	connect("input_event", _on_input)

func _on_enter():  hovered = true;  _apply_colour()
func _on_exit():   hovered = false; _apply_colour()

func _on_input(_v, ev, _s):
	if ev is InputEventMouseButton and ev.button_index == MOUSE_BUTTON_LEFT and ev.pressed:
		idx = (idx + 1) % colours.size()
		_apply_colour()

func _apply_colour():
	var base: Color = colours[idx]   # ✅ explicitly typed
	sprite.modulate = base.darkened(1.0 - dim_amount) if hovered else base
