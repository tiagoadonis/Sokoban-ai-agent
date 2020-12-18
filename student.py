import asyncio
import getpass
import json
import os
import websockets
from mapa import Map
from consts import Tiles
from search import *
from grid import *


ant_level = 1
async def solver(puzzle, solution):
    
    while True:
        game_properties = await puzzle.get()
        print("GAME PROPERTIES: "+str(game_properties))
    
        #print(game_properties["map"])
        print("levels/" + str(ant_level) + ".xsb")
        mapa = Map("levels/" + str(ant_level) + ".xsb")       
        boxes, keeper, goal = get_grid("levels/" + str(ant_level) + ".xsb")
        print(goal)
        # Criar o dominio
        domain = SokobanDomain(mapa, boxes, keeper, goal)
        sokoban = domain.sokoban

        # Localização do Sokoban
        print("Sokoban Pos: "+str(sokoban))

        # Localização das caixas
        boxes = tuple(tuple(i) for i in domain.boxes)
        print("Boxes: "+str(boxes))

        # Caixas nos diamantes (apenas retorna o número de caixas no objetivo, não a localização)
        boxesOnGoal = domain.mapa.on_goal
        print("Boxes on goal: "+str(boxesOnGoal))

        # Posições dos objetivos livres (objetivos onde falta colocar a caixa)
        emptyGoals = domain.mapa.empty_goals
        print("Empty goals: "+str(emptyGoals))

        # Caixas que não estão nos objetivos
        boxTiles = list(domain.mapa.filter_tiles(Tiles.BOX))
        floor = list(domain.mapa.filter_tiles(Tiles.FLOOR))
        
        boxesNotInGoal = []
        count = 0
        t = ()

        for i in boxTiles:
            for j in floor:
                if (i[0] == j[0]) and (i[1] == j[1]):
                    count += 1
            if(count == 0):
                boxesNotInGoal += [i]
            count = 0

        print("Boxes Not In Goal: "+str(boxesNotInGoal))

        keys = []
        # Retorna todas as posições de deadlock do mapa
        # A caixa não pode ir para uma destas posições
        # TODO: 
        # Falta calcular todas as posições entre duas posições de deadlock que estejam junto a uma parede sem um objetivo 
        # Para o 1º nível basta os cantos
        def getDeadlockPositions(realWalls, floors):
            corners = []
            for wall_1 in realWalls:
                for wall_2 in realWalls:
                    x = abs(wall_1[0] - wall_2[0])
                    y = abs(wall_1[1] - wall_2[1])
                    if (x == 1 and y == 1):
                        corners += [(wall_1, wall_2)]
                    
            for a,b in corners:
                for c,d in corners:
                    if a == d and b == c:
                        corners.remove((c,d)) 

            cornersFloor = []
            print("corner")
            print(corners)
            for corner in corners:
                count = 0
                for goal in emptyGoals:
                    if corner[0][0] == goal[0] and corner[1][1] == goal[1]:
                        count += 1
                    if count == 0:
                        if (corner[0][0], corner[1][1]) in floors:
                            cornersFloor += [(corner[0][0], corner[1][1])]
                        else:
                            cornersFloor += [(corner[1][0], corner[0][1])] 
            
            deadlock = cornersFloor
            deadlock = [d for d in deadlock if d not in emptyGoals]
            return deadlock    
                      
        
        walls = list(domain.mapa.filter_tiles(Tiles.WALL))
        floors = list(domain.mapa.filter_tiles(Tiles.FLOOR)) 
        
        # A variável 'realWalls' tem as coordenadas de todas as paredes do jogo
        realWalls = []                
        for wall in walls:
            count = 0
            for floor in floors:
                if(wall[0] == floor[0] and wall[1] == floor[1]):
                    count += 1
            if(count == 0):
                realWalls += [wall]                     

        # DeadlockPos apenas tem os cantos do mapa
        deadlockPos = getDeadlockPositions(realWalls, floors)
        print("REAL WALLS: "+str(realWalls))               

        print("ALL DEADLOCK POSITIONS: "+str(deadlockPos))
        domain.setDeadlockPositions(deadlockPos)

        goal = mapa.filter_tiles([Tiles.GOAL, Tiles.MAN_ON_GOAL, Tiles.BOX_ON_GOAL])
        print("GOAL: "+str(goal))

        problem = SearchProblem(domain, tuple(tuple(i) for i in domain.state), goal)
        print("DOMAIN STATE: "+str(domain.state))

        gen_task = loop.create_task(SokobanTree(problem).search())
        await gen_task
        array = gen_task.result()

        keys = ""+"".join(array)

        print("KEYS: "+str(keys))

        await asyncio.sleep(0)
        await solution.put(keys)

async def agent_loop(puzzle, solution, server_address="localhost:8000", agent_name="student"):
    async with websockets.connect(f"ws://{server_address}/player") as websocket:

        # Receive information about static game properties
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))
        global ant_level
        while True:
            try:
                update = json.loads(
                    await websocket.recv()
                ) # receive game update

                if "map" in update:
                    # we got a new level
                    print(update)
                    game_properties = update
                    keys = ""
                    await puzzle.put(game_properties)

                if "level" in update and ant_level != update["level"]:
                    # we got a new level
                    game_properties = update
                    keys = ""
                    await puzzle.put(game_properties)
                    ant_level = update["level"]

                if not solution.empty():
                    keys = await solution.get()

                key = ""
                if len(keys): #we got a solution
                    key = keys[0]
                    keys = keys[1:]

                await websocket.send(
                    json.dumps({"cmd": "key", "key": key})
                )
            except websockets.exceptions.ConnectionClosedOK:
                print("Server has cleanly disconnected us")
                return

# Sokoban Domain
class SokobanDomain(SearchDomain):
    # Construtor
    def __init__(self, mapa, boxes, keeper, goal):
        self.mapa = mapa
        self.sokoban = keeper
        self.boxes = boxes
        # O estado tem que ter informação de todas as posições dos objetos (caixas e sokoban)
        self.state = tuple((self.sokoban, self.boxes))
        self.goal = goal
 
    # Dada uma posição (state), deve retornar as teclas disponiveis 
    # (só aquelas em que se pode carregar para se ir para uma posição livre)
    def actions(self, state):
        #print("-----------------------------------------------------")
        #print("STATE DENTRO DO ACTIONS: "+str(state))
        actlist = []
        x_sokoban, y_sokoban = state[0]

        # Se a posição em cima do sokoban não for uma parede
        if (not self.mapa.is_blocked((x_sokoban, y_sokoban - 1))):
            count = 0
            for box in state[1]:
                x_box, y_box = box
                # Se a posição em cima do sokoban for uma caixa
                if ((x_sokoban == x_box) and (y_sokoban - 1 == y_box)):
                    for deadState in self.deadlockPos:
                        if (deadState[0] == x_box and deadState[1] == y_box - 1):
                            count += 1
                    # Se a posição em cima da caixa anterior for uma parede
                    if (self.mapa.is_blocked((x_sokoban, y_sokoban - 2))):
                        count += 1
                    for box2 in state[1]: 
                        x_box2, y_box2 = box2
                        if((box2 != box)):
                            # Se a posição em cima da caixa anterior for outra caixa
                            if ((x_box2 == x_box) and (y_box2 - 1 == y_box) or (x_box2 == x_box) and (y_box2 == y_box - 1)):
                                count += 1
            if (count == 0):
                actlist += ["w"]
        # Se a posição à esquerda do sokoban não for uma parede
        if (not self.mapa.is_blocked((x_sokoban - 1, y_sokoban))):
            count = 0
            for box in state[1]:
                x_box, y_box = box        
                # Se a posição à esquerda do sokoban for uma caixa
                if ((x_sokoban - 1 == x_box) and (y_sokoban == y_box)):
                    for deadState in self.deadlockPos:
                        if (deadState[0] == x_box - 1 and deadState[1] == y_box):
                            count += 1
                    # Se a posição à esquerda da caixa anterior for uma parede
                    if (self.mapa.is_blocked((x_sokoban - 2, y_sokoban))):
                        count += 1
                    for box2 in state[1]:
                        x_box2, y_box2 = box2
                        if((box2 != box)):
                            # Se a posição à esquerda da caixa anterior for outra caixa
                            if ((x_box2 - 1 == x_box) and (y_box2 == y_box) or (x_box2 == x_box - 1) and (y_box2 == y_box)):
                                count += 1
            if (count == 0):
                actlist += ["a"]
        # Se a posição em baixo do sokoban não for uma parede
        if (not self.mapa.is_blocked((x_sokoban, y_sokoban + 1))):
            count = 0
            for box in state[1]:
                x_box, y_box = box
                # Se a posição em baixo do sokoban for uma caixa
                if ((x_sokoban == x_box) and (y_sokoban + 1 == y_box)):
                    for deadState in self.deadlockPos:
                        if (deadState[0] == x_box and deadState[1] == y_box + 1):
                            count += 1
                    # Se a posição em baixo da caixa anterior for uma parede
                    if (self.mapa.is_blocked((x_sokoban, y_sokoban + 2))):
                        count += 1
                    for box2 in state[1]:
                        x_box2, y_box2 = box2
                        if((box2 != box)):
                            # Se a posição em baixo da caixa anterior for outra caixa
                            if ((x_box2 == x_box) and (y_box2 + 1 == y_box) or (x_box2 == x_box) and (y_box2 == y_box + 1)):
                                count += 1
            if (count == 0):
                actlist += ["s"]
        # Se a posição à direita do sokoban não for uma parede
        if (not self.mapa.is_blocked((x_sokoban + 1, y_sokoban))):
            count = 0
            for box in state[1]:
                x_box, y_box = box
                # Se a posição à direita do sokoban for uma caixa
                if ((x_sokoban + 1 == x_box) and (y_sokoban == y_box)):
                    for deadState in self.deadlockPos:
                        if (deadState[0] == x_box + 1 and deadState[1] == y_box):
                            count += 1
                    # Se a posição à direita da caixa anterior for uma parede
                    if (self.mapa.is_blocked((x_sokoban + 2, y_sokoban))):
                        count += 1
                    for box2 in state[1]:
                        x_box2, y_box2 = box2
                        if((box2 != box)):
                            # Se a posição à direita da caixa anterior for outra caixa
                            if ((x_box2 + 1 == x_box) and (y_box2 == y_box) or (x_box2 == x_box + 1) and (y_box2 == y_box)):
                                count += 1
            if (count == 0):
                actlist += ["d"]
        #print("ACTLIST: "+str(actlist))
        return actlist

    # Dada uma posição (state) e tecla (action), retornar a nova posição atualizada no state
    def result(self, state, action):
        #print("STATE INSIDE RESULT: "+str(state))
        x_sokoban, y_sokoban = state[0]
        if action == "w":
            boxes = []
            i = 0
            newSokobanPos = (x_sokoban, y_sokoban - 1)
            for box in state[1]:
                x_box, y_box = box
                # Caso o sokoban se mova e arraste uma caixa para cima
                if ((x_sokoban == x_box) and (y_sokoban - 1 == y_box)):
                    # Atualiza a posição da caixa
                    boxes.insert(i, (x_box, y_box - 1))    
                else:
                    boxes.insert(i, (x_box, y_box))
                i += 1
            # Atualiza a posição do sokoban
            state = tuple((newSokobanPos, boxes))
            #print("STATE com 'w': "+str(state))
        elif action == "a":
            boxes = []
            i = 0
            newSokobanPos = (x_sokoban - 1, y_sokoban)
            for box in state[1]:
                x_box, y_box = box
                # Caso o sokoban se mova e arraste uma caixa para a esquerda
                if ((x_sokoban - 1 == x_box) and (y_sokoban == y_box)):
                    # Atualiza a posição da caixa
                    boxes.insert(i, (x_box - 1, y_box)) 
                else:
                    boxes.insert(i, (x_box, y_box))
                i += 1
            # Atualiza a posição do sokoban
            state = tuple((newSokobanPos, boxes))
            #print("STATE com 'a': "+str(state))
        elif action == "s":
            boxes = []
            i = 0
            newSokobanPos = (x_sokoban, y_sokoban + 1)
            for box in state[1]:
                x_box, y_box = box
                # Caso o sokoban se mova e arraste uma caixa para baixo
                if ((x_sokoban == x_box) and (y_sokoban + 1 == y_box)):
                    # Atualiza a posição da caixa
                    boxes.insert(i, (x_box, y_box + 1)) 
                else:
                    boxes.insert(i, (x_box, y_box))                    
                i += 1
            # Atualiza a posição do sokoban
            state = tuple((newSokobanPos, boxes))            
            #print("STATE com 's': "+str(state))
        elif action == "d":
            boxes = []
            i = 0
            newSokobanPos = (x_sokoban + 1, y_sokoban)
            for box in state[1]:
                x_box, y_box = box
                # Caso o sokoban se mova e arraste uma caixa para a direita
                if ((x_sokoban + 1 == x_box) and (y_sokoban == y_box)):
                    # Atualiza a posição da caixa
                    boxes.insert(i, (x_box + 1, y_box))
                else:
                    boxes.insert(i, (x_box, y_box))
                i += 1
            # Atualiza a posição do sokoban
            state = tuple((newSokobanPos, boxes))
            #print("STATE com 'd': "+str(state))
        #print("RETURN STATE FROM RESULT: "+str(state))
        return state

    # Custo de cada movimento
    def cost(self, state, action):
        return 1

    # Para cada caixa ver qual o diamante mais próximo e somar as distancias
    def heuristic(self, state, goal):
        min = 1000
        heur = 0
        for box in state[1]:
            for g in goal:
                dist = ( (box[0] - g[0])**2 + (box[1] - g[1])**2 )**(1/2) 
                if (dist < min):
                    # Distância mínima de uma caixa ao diamante
                    min = dist      
            # Soma á heuristica o valor mínimo de uma caixa, para todas as iteraçẽs das caixas
            heur += min             
            # Volta a colocar o mínimo a 1000 para que se possa encontrar uma nova distância mínima para outra caixa
            min = 1000              
        return heur

    # Para armazenar as deadlock positions
    def setDeadlockPositions(self, deadlockPos):
        self.deadlockPos = deadlockPos

# DO NOT CHANGE THE LINES BELLOW
# You can change the default values using the command line, example:
# $ NAME='arrumador' python3 client.py
loop = asyncio.get_event_loop()
SERVER = os.environ.get("SERVER", "localhost")
PORT = os.environ.get("PORT", "8000")
NAME = os.environ.get("NAME", getpass.getuser())

puzzle = asyncio.Queue(loop=loop)
solution = asyncio.Queue(loop=loop)

net_task = loop.create_task(agent_loop(puzzle, solution, f"{SERVER}:{PORT}", NAME))
solver_task = loop.create_task(solver(puzzle, solution))

loop.run_until_complete(net_task)
