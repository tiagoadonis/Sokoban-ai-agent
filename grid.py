# Get grid-like map and boxes coordinates, and goal coordinates  | status: done
def get_grid(map_lvl):

    mapa = open(map_lvl,'r')
    boxes = []
    goals = []
    keeper = ()
    
    x=y=0
    for line in mapa:
        for symbol in line:
            
            if symbol == ".":
                goals.append((x,y))
            if symbol == "@":
                keeper=(x,y)
            if symbol == "+":
                keeper=(x,y)
                goals.append((x,y))
            if symbol == "$":
                boxes.append((x,y))
            if symbol == "*":
                boxes.append((x,y))
                goals.append((x,y))
            x += 1
        y += 1
        x = 0

    return boxes,keeper,goals