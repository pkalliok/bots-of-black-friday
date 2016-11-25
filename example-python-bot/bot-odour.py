from flask import Flask, request, jsonify, Response
import requests, random
from json import dumps, loads
import heatmap
bot = Flask(__name__)

server_url = 'http://localhost:8080' # CHANGE
port = 8777
move_endpoint = '/api/move'
my_address = 'http://localhost:%d%s' % (port, move_endpoint)

@bot.route('/api/ping')
def ping(): return "pong\n"

mymap = None

@bot.route('/api/register/<nick>', methods=['POST'])
def register(nick):
    response = requests.post("%s/register" % server_url,
            json=dict(playerName=nick, url=my_address))
    state = response.json()
    return jsonify(state['player'])

move_resp = dict((move, Response('"%s"' % move, mimetype='application/json'))
        for move in ('UP', 'DOWN', 'LEFT', 'RIGHT', 'PICK', 'USE'))

@bot.route(move_endpoint, methods=['POST'])
def move():
    global mymap
    state = request.get_json()
    loc = get_player_location(state)
    if not mymap:
        map = get_in(state, 'gameState', 'map')
        mymap = heatmap.new_map(map['width'], map['height'])
    money = get_in(state, 'playerState', 'money')
    for (value, (x, y)) in items_by_value(get_in(state, 'gameState', 'items'), money):
        print("Item of value %s at %s" % (value, (x, y)))
        mymap[y][x] = value
    for (x, y) in player_locations(get_in(state, 'gameState', 'players')):
        mymap[y][x] = -10
    x, y = position_to_location(get_in(state, 'gameState', 'map', 'exit'))
    mymap[y][x] = 5000 - money
    mymap = heatmap.blur(mymap)
    update_heatmap_from_gamemap(mymap, get_in(state, 'gameState', 'map', 'tiles'))
    heatmap.print_map(mymap)
    possible_moves = get_legal_moves(state, loc)
    if 'PICK' in possible_moves: my_move = 'PICK'
    elif 'USE' in possible_moves: my_move = 'USE'
    else: my_move = pick_best(possible_moves)
    print("Currently at %s, possible moves are %s, going to do %s" %
            (loc, possible_moves, my_move))
    return move_resp[my_move]

def player_locations(players):
    return (position_to_location(player['position'])
            for player in players)

def update_heatmap_from_gamemap(heatmap, gamemap):
    for y in range(len(heatmap)):
        for x in range(len(heatmap[y])):
            if gamemap[y][x] == 'x': heatmap[y][x] = 0

def pick_best(possible_moves):
    print("Possible moves: %s" % possible_moves)
    global mymap
    goodness = -300
    move = possible_moves[0][0]
    for (new_move, (x, y)) in possible_moves:
        new_goodness = heatmap.get_map(mymap, x, y)
        print("Move %s goodness %s" % (new_move, new_goodness))
        if new_goodness >= goodness:
            goodness = new_goodness
            move = new_move
    return move

def items_by_value(itemlist, moneyLeft):
    return sorted(
        (item['price'] * item['discountPercent'] / 100., position_to_location(item['position']))
        for item in itemlist if real_price(item) <= moneyLeft)

def get_in(state, *args):
    if not args: return state
    return get_in(state[args[0]], *args[1:])

def get_player_location(state):
    pos = get_in(state, 'playerState', 'position')
    return position_to_location(pos)

def position_to_location(pos): return (pos['x'], pos['y'])

def get_tile_at(state, location):
    x, y = location
    map = get_in(state, 'gameState', 'map', 'tiles')
    return map[y][x]

def delta(loc, delta):
    return (loc[0] + delta[0], loc[1] + delta[1])

def get_legal_moves(state, location):
    return get_legal_directions(state, location) + \
            get_legal_actions(state, location)

def get_legal_directions(state, location):
    return [(direction[0], delta(location, direction[1]))
            for direction in (('UP', (0, -1)), ('DOWN', (0, 1)),
                ('LEFT', (-1, 0)), ('RIGHT', (1, 0)))
            if get_tile_at(state, delta(location, direction[1])) != 'x']

def get_legal_actions(state, location):
    money = get_in(state, 'playerState', 'money')
    num_players = len(get_in(state, 'gameState', 'players'))
    item_locs = (position_to_location(item['position'])
            for item in get_in(state, 'gameState', 'items')
            if real_price(item) <= money)
    return (['PICK'] if location in item_locs else []) \
            + (['USE'] if get_in(state, 'playerState', 'usableItems') and num_players > 1 else [])

def real_price(item):
    return item['price'] * (100 - item['discountPercent']) / 100.

if __name__ == '__main__': bot.run(host='0.0.0.0', port=port, debug=True)

