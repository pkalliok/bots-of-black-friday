from flask import Flask, request, jsonify, Response
import requests, random, heatmap
from json import dumps, loads
bot = Flask(__name__)

server_url = 'http://localhost:8080' # CHANGE
port = 8774
move_endpoint = '/api/move'
my_address = 'http://localhost:%d%s' % (port, move_endpoint)

@bot.route('/api/ping')
def ping(): return "pong\n"

@bot.route('/api/register/<nick>', methods=['POST'])
def register(nick):
    response = requests.post("%s/register" % server_url,
            json=dict(playerName=nick, url=my_address))
    return jsonify(response.json()['player'])

move_resp = dict((move, Response('"%s"' % move, mimetype='application/json'))
        for move in ('UP', 'DOWN', 'LEFT', 'RIGHT', 'PICK', 'USE'))

@bot.route(move_endpoint, methods=['POST'])
def move():
    state = request.get_json()
    loc = get_player_location(state)
    money = get_in(state, 'playerState', 'money')
    health = get_in(state, 'playerState', 'health')
    gamemap = get_in(state, 'gameState', 'map', 'tiles')
    maps = get_item_maps(gamemap, get_in(state, 'gameState', 'items'), money) + \
            get_exit_map(gamemap, get_in(state, 'gameState', 'map', 'exit'), health, money)
            #get_player_maps(gamemap, get_in(state, 'gameState', 'players')) + \
    #for map in maps: heatmap.linear_print_map(map)
    goodness_map = reduce(heatmap.add_maps, maps)
    #heatmap.linear_print_map(goodness_map)
    for y in range(loc[1]-2, loc[1]+3):
        print goodness_map[y][loc[0]-2:loc[0]+3]
    possible_moves = get_legal_moves(state, loc)
    if 'PICK' in possible_moves: my_move = 'PICK'
    elif 'USE' in possible_moves: my_move = 'USE'
    else: my_move = pick_best(possible_moves, goodness_map)
    print("Currently at %s, possible moves are %s, going to do %s" %
            (loc, possible_moves, my_move))
    return move_resp[my_move]

def get_item_maps(gamemap, items, money):
    return [heatmap.spreadmap_by_corridors(gamemap, x, y, -10. * value)
            for (value, (x, y)) in items_by_value(items, money)]

def get_player_maps(gamemap, players):
    return [heatmap.spreadmap_by_corridors(gamemap, x, y, 1)
            for (x, y) in player_locations(players)]

def get_exit_map(gamemap, exit, health, money):
    x, y = position_to_location(exit)
    should_not_exit = (money/100.)-8.
    health_multiplier = 1.+(100./health)
    return [heatmap.spreadmap_by_corridors(gamemap, x, y, -2. * health_multiplier)]

def items_by_value(itemlist, moneyLeft):
    return ((item['discountPercent'], position_to_location(item['position']))
        for item in itemlist if real_price(item) <= moneyLeft)

def player_locations(players):
    return (position_to_location(player['position'])
            for player in players)

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

def pick_best(possible_moves, goodness_map):
    print("Possible moves: %s" % possible_moves)
    goodness = -3000000
    move = possible_moves[0][0]
    for (new_move, (x, y)) in possible_moves:
        new_goodness = heatmap.get_map(goodness_map, x, y)
        print("Move %s goodness %s" % (new_move, new_goodness))
        if new_goodness >= goodness:
            goodness = new_goodness
            move = new_move
    return move

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

