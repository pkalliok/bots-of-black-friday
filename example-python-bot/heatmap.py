
def new_map(width, height):
    return [[0] * width for _ in range(height)]

def blur_a_lot(map):
    return blur(blur(blur(blur(map))))

def blur(map):
    return [[average_surround(map, x, y) for x in range(len(map[y]))]
            for y in range(len(map))]

def spreadmap_by_corridors(tiles, x, y, scale):
    result = new_map(len(tiles[0]), len(tiles))
    places_to_try = [(x, y, scale)]
    while places_to_try:
        new_places_to_try = []
        for x, y, value in places_to_try:
            if result[y][x] != 0: continue
            if tiles[y][x] == 'x': continue
            result[y][x] = value
            new_places_to_try.append((x-1, y, value + scale))
            new_places_to_try.append((x+1, y, value + scale))
            new_places_to_try.append((x, y-1, value + scale))
            new_places_to_try.append((x, y+1, value + scale))
        places_to_try = new_places_to_try
        scale = scale * 0.9
    return result

def add_maps(map1, map2):
    return [[item1 + item2 for item1, item2 in zip(row1, row2)]
            for row1, row2 in zip(map1, map2)]

def get_map(map, x, y):
    if y < 0 or y >= len(map) or x < 0 or x >= len(map[y]): return 0
    return map[y][x]

def average_surround(map, x, y):
    return (get_map(map, x, y) + get_map(map, x-1, y) +
            get_map(map, x+1, y) + get_map(map, x, y-1) +
            get_map(map, x, y+1)) / 5.

def linear_print_map(map):
    for row in map:
        print(''.join('0123456789'[int(value/3000)+7] for value in row))

def print_map(map):
    for row in map:
        print(''.join(visual_char(value) for value in row))

def visual_char(value):
    if value > 1000: return "#"
    if value > 300: return "*"
    if value > 100: return "+"
    if value > 30: return "-"
    if value > 10: return ";"
    if value > 3: return ","
    if value > 1: return "."
    if value < -3: return "@"
    if value < -1: return "&"
    if value < 0: return "~"
    return " "

