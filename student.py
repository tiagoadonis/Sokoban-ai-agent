import asyncio
import getpass
import json
import os

import websockets
from mapa import Map
from consts import Tiles
from search import *

async def agent_loop(server_address="localhost:8000", agent_name="student"):
    async with websockets.connect(f"ws://{server_address}/player") as websocket:

        # Receive information about static game properties
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))
        msg = await websocket.recv()
        game_properties = json.loads(msg)

        # You can create your own map representation or use the game representation:
        mapa = Map(game_properties["map"])
        print(mapa)

        while True:
            try:
                state = json.loads(
                    await websocket.recv()
                )  # receive game state, this must be called timely or your game will get out of sync with the server

                # ----------------------------------------------- Testes ------------------------------------------------------
                # Criar o dominio
                domain = SokobanDomain(mapa, state)
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

                #path = ["s"]

                # --------------------------------------------- Fim dos testes --------------------------------------------------
                path = []

                # # retorna a posição para onde o sokoban tem de ir para mover a caixa
                # def moveBox(box,action):
                #     x_pos, y_pos = box
                #     if action == 'w':
                #         return (x_pos, y_pos+1)
                #     elif action == 's':
                #         return (x_pos, y_pos-1)
                #     elif action == 'a':
                #         return (x_pos+1, y_pos)
                #     elif action == 'd':
                #         return (x_pos-1, y_pos)

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

                    return cornersFloor                  
                
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

                corners = getDeadlockPositions(realWalls, floors)
                print("REAL WALLS: "+str(realWalls))
                print("CORNERS: "+str(corners))                 
    
                goal = mapa.filter_tiles([Tiles.GOAL, Tiles.MAN_ON_GOAL, Tiles.BOX_ON_GOAL])
                print("GOAL: "+str(goal))

                problem = SearchProblem(domain, tuple(tuple(i) for i in domain.state), goal)
                print("DOMAIN STATE: "+str(domain.state))

                pathTest = SokobanTree(problem).search()
                print("PATH: "+str(pathTest))

                print("-------------------------------------------------------")
                if path == []:
                    continue
                else:
                    await websocket.send(
                        json.dumps({"cmd": "key", "key": path.pop(0)})
                    )

            except websockets.exceptions.ConnectionClosedOK:
                print("Server has cleanly disconnected us")
                return

# Sokoban Domain
class SokobanDomain(SearchDomain):
    # Construtor
    def __init__(self, mapa, state):
        self.mapa = mapa
        self.sokoban = state["keeper"]
        self.boxes = state["boxes"]
        # O estado tem que ter informação de todas as posições dos objetos (caixas e sokoban)
        self.state = tuple((self.sokoban, self.boxes))
 
    # Dada uma posição (state), deve retornar as teclas disponiveis 
    # (só aquelas em que se pode carregar para se ir para uma posição livre)
    def actions(self, state):
        print("-----------------------------------------------------")
        print("STATE DENTRO DO ACTIONS: "+str(state))
        actlist = []
        x_sokoban, y_sokoban = state[0]
        
        #-----------------------------------------------------------------------------------------------
        # Se a posição em cima do sokoban for uma parede
        if (not self.mapa.is_blocked((x_sokoban, y_sokoban - 1))):
            #print("POSIÇÃO DESBLOQUEADA")
            count = 0
            for box in state[1]:
                #print("CICLO DAS CAIXAS")
                x_box, y_box = box

                print("CAIXA DO PRIMEIRO CICLO: "+str(box))

                # Se a posição em cima do sokoban for uma caixa
                if ((x_sokoban == x_box) and (y_sokoban - 1 == y_box)):
                    # Se a posição em cima da caixa anterior for uma parede
                    if (self.mapa.is_blocked((x_sokoban, y_sokoban - 2))):
                        count += 1
                    for box2 in state[1]:
                        #print("SEGUNDO CICLO DAS CAIXAS")
                        x_box2, y_box2 = box2

                        print("CAIXA 1 -> "+str(box))
                        print("CAIXA 2 -> "+str(box2))

                        # Se a posição em cima da caixa anterior for outra caixa
                        if ((x_box2 == x_box) and (y_box2 - 1 == y_box)):
                            print("CAIXA EM CIMA DE OUTRA CAIXA!!!!!!!!!")
                            count += 1
            #print("COUNT: "+str(count))
            if (count == 0):
                actlist += ["w"]
            #-------------------------------------------------------------------------------------

        # Se a posição à esquerda do sokoban for uma parede
        if (not self.mapa.is_blocked((x_sokoban - 1, y_sokoban))):
            count = 0
            for box in state[1]:
                x_box, y_box = box        
                # Se a posição à esquerda do sokoban for uma caixa
                if ((x_sokoban - 1 == x_box) and (y_sokoban == y_box)):
                    # Se a posição à esquerda da caixa anterior for uma parede
                    if (self.mapa.is_blocked((x_sokoban - 2, y_sokoban))):
                        count += 1
                    for box2 in state[1]:
                        x_box2, y_box2 = box2
                        # Se a posição à esquerda da caixa anterior for outra caixa
                        if ((x_box2 - 1 == x_box) and (y_box2 == y_box)):
                            count += 1
            if (count == 0):
                actlist += ["a"]
        # Se a posição em baixo do sokoban for uma parede
        if (not self.mapa.is_blocked((x_sokoban, y_sokoban + 1))):
            count = 0
            for box in state[1]:
                x_box, y_box = box
                # Se a posição em baixo do sokoban for uma caixa
                if ((x_sokoban == x_box) and (y_sokoban + 1 == y_box)):
                    # Se a posição em baixo da caixa anterior for uma parede
                    if (self.mapa.is_blocked((x_sokoban, y_sokoban + 2))):
                        count += 1
                    for box2 in state[1]:
                        x_box2, y_box2 = box2
                        # Se a posição em baixo da caixa anterior for outra caixa
                        if ((x_box2 == x_box) and (y_box2 + 1 == y_box)):
                            count += 1
            if (count == 0):
                actlist += ["s"]
        # Se a posição à direita do sokoban for uma parede
        if (not self.mapa.is_blocked((x_sokoban + 1, y_sokoban))):
            count = 0
            for box in state[1]:
                x_box, y_box = box
                # Se a posição à direita do sokoban for uma caixa
                if ((x_sokoban + 1 == x_box) and (y_sokoban == y_box)):
                    # Se a posição à direita da caixa anterior for uma parede
                    if (self.mapa.is_blocked((x_sokoban + 2, y_sokoban))):
                        count += 1
                    for box2 in state[1]:
                        x_box2, y_box2 = box2
                        # Se a posição à direita da caixa anterior for outra caixa
                        if ((x_box2 + 1 == x_box) and (y_box2 == y_box)):
                            count += 1
            if (count == 0):
                actlist += ["d"]
        print("ACTLIST: "+str(actlist))
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

# DO NOT CHANGE THE LINES BELLOW
# You can change the default values using the command line, example:
# $ NAME='arrumador' python3 client.py
loop = asyncio.get_event_loop()
SERVER = os.environ.get("SERVER", "localhost")
PORT = os.environ.get("PORT", "8000")
NAME = os.environ.get("NAME", getpass.getuser())
loop.run_until_complete(agent_loop(f"{SERVER}:{PORT}", NAME))