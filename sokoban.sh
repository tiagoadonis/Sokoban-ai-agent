#! /bin/bash

clear

gnome-terminal --tab --title="server.py" --working-directory='/home/tiagoadonis/Desktop/Universidade/4_ano/IIA/Projeto/venv' -- /bin/bash -c "source ./bin/activate && cd ../ZonaDeTrabalho && python3 server.py; exec /bin/bash" 

gnome-terminal --tab --title="viewer.py" --working-directory='/home/tiagoadonis/Desktop/Universidade/4_ano/IIA/Projeto/venv' -- /bin/bash -c "source ./bin/activate && cd ../ZonaDeTrabalho && python3 viewer.py; exec /bin/bash" 

gnome-terminal --tab --title="student.py" --working-directory='/home/tiagoadonis/Desktop/Universidade/4_ano/IIA/Projeto/venv' -- /bin/bash -c "source ./bin/activate && cd ../ZonaDeTrabalho && python3 student.py; exec /bin/bash" 
