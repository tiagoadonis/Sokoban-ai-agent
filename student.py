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
                boxes = domain.boxes
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

                # if (len(boxesNotInGoal) > 0):
                #     for boxes in boxesNotInGoal:
                #         corner = preventDeadlock(boxes)        
                #         problem = SearchProblem(domain, sokoban, corner)
                #         path = SokobanTree(problem).search()
                #         print("PATH: "+str(path))

                # for boxes in boxesNotInGoal:
                #     problem = SearchProblem(domain, boxes, emptyGoals.pop(0))
                #     pathBoxToGoal = SokobanTree(problem).search()
                #     print("PATH BOX TO GOAL: "+str(pathBoxToGoal))

                #     print("FIRST STEP: "+str(pathBoxToGoal[0]))
                    
                    # newPos = domain.result(boxes, pathBoxToGoal[0])            
                    # print("BOX GOES TO: "+str(newPos))

                # newPos = preventDeadlock(boxesNotInGoal.pop(0))
                # print("VAI PARA -> "+str(newPos))

                # problem = SearchProblem(domain, sokoban, newPos)
                # path = SokobanTree(problem).search()
                # print("CAMINHO: "+str(path))

                # nextPos = domain.result(sokoban, path[0])
                # print("NEXT POS: "+str(nextPos))

                # actList = domain.actions(sokoban)

                # newActlist = possibleToMove(sokoban, actList, boxes)
                # print("TECLAS DISPONIVEIS: "+str(newActlist))

                # blocked = nextPosIsBlocked(boxes, nextPos)
                # print("NEXT POSITION IS BLOCKED: "+str(blocked))

                # if (blocked):
                #     path = list(reversed(path))

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

                # Verifica se a posição passada é uma posição de deadlock
                # def originateDeadlock(deadlockPos, state):
                #     for pos in deadlockPos:
                #         if pos[0] == state[0] and pos[1] == state[1]:
                #             return True
                #     return False                  

                # for box in boxesNotInGoal:
                #     for goal in emptyGoals:
                #         problem = SearchProblem(domain, box, goal)
                #         pathBoxToGoal = SokobanTree(problem).search()
                #         print("PATH BOX TO GOAL: "+str(pathBoxToGoal))
                #         # Verifica se ao mover a caixa não cria uma situação de deadlock
                #         movePosBox = domain.result(box, pathBoxToGoal[0])
                #         deadlock = originateDeadlock(corners, movePosBox)
                #         # Se criar uma posição de deadlock tem que gerar outro caminho
                #         if deadlock == True:
                #             # dada a posição -> devolve as teclas disponíveis a partir dessa posição
                #             # TODO
                #             actList = domain.actions(box)
                #             print("ACTLIST: "+str(actList))
                #         # Caso o caminho não crie uma posição de deadlock
                #         else:
                #             # Posição para onde o sokoban tem que se deslocar para mover a caixa para a direção pretendida
                #             newPos = moveBox(box, pathBoxToGoal[0])
                #             print("SOKOBAN VAI PARA -> "+str(newPos))
                #             # Verifica se a posição para onde o sokoban tem que se deslocar está bloqueada ou não
                #             print("NEW POS IS BLOCKED: "+str(mapa.is_blocked(newPos)))
                #             if mapa.is_blocked(newPos) == True:
                #                 # Se a posição para onde o sokoban tem que se deslocar estiver bloqueada é necessário encontrar
                #                 # outra posição
                #                 actList = domain.actions(box)
                #                 print("ACTLIST: "+str(actList))
                #                 actList.remove(pathBoxToGoal[0])
                #                 print("NEW ACTLIST: "+str(actList))
                #                 # TODO
                #                 # Ver se a nova posição cria um estado de deadlock ou se está disponível        
                                    

                # problem = SearchProblem(domain, sokoban, newPos)
                # path = SokobanTree(problem).search()

                # print("------------------------RESULT-------------------------")
                # domain.result(state, "w")

                newState = list(domain.state)
                newState[0] = [2,5]
                
                print("NEW STATE: "+str(newState))
                problem = SearchProblem(domain, domain.state, tuple(newState))
                
                #print("PROBLEM GOAL: "+str(problem.goal[0]))
                
                pathTest = SokobanTree(problem).search()
                print("PATH TO (2,5): "+str(pathTest))

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
        actlist = []
        x_sokoban, y_sokoban = state[0]
        # Se a posição em cima do sokoban for uma parede
        if (not self.mapa.is_blocked((x_sokoban, y_sokoban - 1))):
            count = 0
            for box in state[1]:
                x_box, y_box = box
                # Se a posição em cima do sokoban for uma caixa
                if ((x_sokoban == x_box) and (y_sokoban - 1 == y_box)):
                    # Se a posição em cima da caixa anterior for uma parede
                    if (self.mapa.is_blocked((x_sokoban, y_sokoban - 2))):
                        count += 1
                    for box2 in state[1]:
                        x_box2, y_box2 = box2
                        # Se a posição em cima da caixa anterior for outra caixa
                        if ((x_box2 == x_box) and (y_box2 - 1 == y_box)):
                            count += 1
            if (count == 0):
                actlist += ["w"]
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

        return actlist

    # Dada uma posição (state) e tecla (action), retornar a nova posição atualizada no state
    def result(self, state, action):
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

    # Definição da heuristica
    # TODO
    # Para cada caixa ver qual o diamante mais próximo e somar as distancias
    def heuristic(self, state, goal):
        count = 0
        sokobanInitial = state[0]
        sokobanFinal = goal[0]
        return ((sokobanFinal[0] - sokobanInitial[0])**2 + (sokobanFinal[1] - sokobanInitial[1])**2)**(1/2)
        
# DO NOT CHANGE THE LINES BELLOW
# You can change the default values using the command line, example:
# $ NAME='arrumador' python3 client.py
loop = asyncio.get_event_loop()
SERVER = os.environ.get("SERVER", "localhost")
PORT = os.environ.get("PORT", "8000")
NAME = os.environ.get("NAME", getpass.getuser())
loop.run_until_complete(agent_loop(f"{SERVER}:{PORT}", NAME))