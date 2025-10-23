import random
import requests
import threading
import time

import zmq
from sympy import ZZ
from sympy.polys.galoistools import gf_multi_eval

from Crypto.generators.Albatross.Albatross import ALBATROSS
from Crypto.generators.Albatross.Proofs.DLEQ import DLEQ
from Crypto.generators.PPVSS.PPVSSHandler import PPVSS
from Network.JSONHandler import JSONHandler
from Network.PriorityExecutor import PriorityExecutor
from Network.collections.DbConstants import DEFL_DOMAIN, DEFL_SET_SIZE, DEFL_PORT
from Network.ledger import Ledger


class Node:
    __instance = None

    @staticmethod
    def getinstance():
        """ Static access method. """
        if Node.__instance is None:
            return None
        return Node.__instance

    def __init__(self, id, node_ip, port, q, p, h, peers=None):
        """ Virtually private constructor. """
        if peers is None:
            peers = []
        if Node.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            Node.__instance = self
            self.running = True  # Saber si el nodo está corriendo por si queremos desconectarnos en algún momento
            self.id = id  # id del nodo
            self.node_ip = node_ip # IP Local
            self.port = port  # Puerto local
            self.peers = peers  # Lista de peers
            self.context = zmq.Context()  # Contexto de ZMQ
            self.router_socket = self.context.socket(zmq.ROUTER)  # Socket ROUTER
            self.router_socket.set_hwm(2000) # High Water Mark
            self.devices = {}  # Dispositivos conectados
            self.myData = set(random.sample(range(DEFL_DOMAIN), DEFL_SET_SIZE))  # Datos propios
            self.domain = DEFL_DOMAIN  # Dominio de los números aleatorios sobre los que se trabaja
            self.results = {}  # Resultados de las intersecciones
            self.json_handler = JSONHandler(self.node_ip, self.myData, self.domain, self.devices, self.results,
                                            self.new_peer)
            self.n = len(self.devices)
            self.ledgers: list[Ledger] = [None] * self.n
            #self.ledgers[id] = Ledger(self.n, q, p, h)
            self.sk = random.randint(0, q-1)
            self.pk = pow(h, self.sk, p)
            self.h = h  # Generador del grupo
            self.q = q  # Orden del subgrupo
            self.p = p  # Módulo de operación
            self.P = []
            self.S = []
            self.neighbors: list[Node] = []
            self.dec_frag = []
            self.executor = PriorityExecutor(max_workers=10)
            # Manejador de esquemas criptográficos

            self.albatross = ALBATROSS(self.h, self.q, self.p, self.n)  # Instancia de Albatross para el manejo de claves
        

    def start(self):
        print(f"Node {self.node_ip} (You) starting...")
        print(f"Node {self.node_ip} (You) - My data: {self.myData}")

        # Iniciar el socket ROUTER en un hilo
        threading.Thread(target=self.start_router_socket).start()
        time.sleep(1)  # Dar tiempo para que el socket ROUTER se inicie

        # Conectar con los peers
        self.connect_to_peers()

    def connect_to_peers(self):
        for peer in self.peers:
            print(f"Node {self.node_ip} (You) connecting to Node {peer}")
            self._connect_to_peer(peer)

    def _connect_to_peer(self, peer):
        dealer_socket = self.context.socket(zmq.DEALER)
        dealer_socket.set_hwm(2000)
        dealer_socket.connect(f"tcp://{peer}:{self.port}")
        dealer_socket.send_string(f"DISCOVER: Node {self.node_ip} is looking for peers")

        # Update devices dictionary
        if "[" in peer and "]" in peer:  # IPv6 address
            address = peer.split("]:")[0] + "]"
        else:  # IPv4 address
            address = peer.split(":")[0]
        self.devices[address] = {"socket": dealer_socket, "last_seen": None}

    def start_router_socket(self):
        if "[" in self.node_ip and "]" in self.node_ip:
            self.router_socket.setsockopt(zmq.IPV6, 1)
        self.router_socket.bind(f"tcp://{self.node_ip}:{self.port}")
        print(f"Node {self.node_ip} (You) listening on port {self.port}")
        threading.Thread(target=self._listen_on_router, daemon=True).start()
        # daemon=True para que el hilo muera cuando el programa principal muera

    def _listen_on_router(self):
        while self.running:
            try:
                sender, message = self.router_socket.recv_multipart()
                if message.startswith(b'{'):
                    self.executor.submit(0, self.json_handler.handle_message, message)
                else:
                    self.executor.submit(1, self._handle_received, sender, message)
            except zmq.ZMQError as e:
                if e.errno == zmq.ETERM:
                    # Context terminated
                    break

    def _handle_received(self, sender, message):
        message = message.decode('utf-8')
        print(f"Node {self.node_ip} (You) received: {message}")
        day_time = time.strftime("%H:%M:%S", time.localtime())
        self.handle_message(sender, message, day_time)

    def handle_message(self, sender, message, day_time):
        # Cleaner routing
        message_handlers = {
            "DISCOVER:": self.handle_discover,
            "DISCOVER_ACK:": self.handle_discover_ack,
            "Added ": self.handle_added
        }
        if message.endswith("is pinging you!"):
            self.handle_ping(sender, message, day_time)
        else:
            for key in message_handlers:
                if message.startswith(key):
                    message_handlers[key](message, day_time)
                    return
            self.handle_unknown(message, day_time)

    def handle_ping(self, sender, message, day_time):
        peer = message.split(" ")[0]
        if peer not in self.devices:
            self.new_peer(peer, day_time)
        self.devices[peer]["last_seen"] = day_time
        self.router_socket.send_multipart([sender, f"{self.node_ip} is up and running!".encode('utf-8')])

    def handle_discover(self, message, day_time):
        peer = message.split(" ")[2]
        if peer not in self.devices:
            self.new_peer(peer, day_time)
        self.devices[peer]["last_seen"] = day_time
        self.devices[peer]["socket"].send_string(f"DISCOVER_ACK: Node {self.node_ip} acknowledges node {peer}")

    def handle_discover_ack(self, message, day_time):
        peer = message.split(" ")[2]
        if peer not in self.devices:
            self.new_peer(peer, day_time)
        self.devices[peer]["last_seen"] = day_time
        self.devices[peer]["socket"].send_string(f"Added {peer} to my network - From Node {self.node_ip}")

    def handle_added(self, message, day_time):
        peer = message.split(" ")[8]
        self.devices[peer]["last_seen"] = day_time

    def handle_unknown(self, message, day_time):
        print(f"{self.node_ip} (You) received: {message} but don't know what to do with it")
        peer = message.split(" ")[0]
        self.devices[peer]["last_seen"] = day_time

    def get_devices(self):
        return {device: info["last_seen"] for device, info in self.devices.items()}

    def ping_device(self, device):
        if device in self.devices:
            print(f"Pinging device: {device}")
            attempts = 0
            max_attempts = 3

            while attempts < max_attempts:
                self.devices[device]["socket"].send_string(f"{self.node_ip} is pinging you!")

                try:
                    reply = self.devices[device]["socket"].recv_string(zmq.DONTWAIT)
                    print(f"{device} - Received: {reply}")

                    if reply.endswith("is up and running!"):
                        self.devices[device]["last_seen"] = time.strftime("%H:%M:%S", time.localtime())
                        print(f"{device} - Ping OK")
                        return device + " - Ping OK"
                    else:
                        print(f"{device} - Ping FAIL - Unexpected response: {reply}")
                        return device + " - Ping FAIL - Unexpected response: " + reply

                except zmq.error.Again:
                    print(f"{device} - Ping FAIL - Retrying...")
                    time.sleep(1)
                    attempts += 1

            print(f"Device {device} - Ping FAIL - Device likely disconnected")
            self.devices[device]["last_seen"] = False
            return device + " - Ping FAIL - Device likely disconnected"
        else:
            print("Device not found")
            return "Device not found"

    def broadcast_message(self, message):
        for device in self.devices:
            self.devices[device]["socket"].send_string(message)

    def stop(self):
        self.running = False
        for device in self.devices:
            self.devices[device]["socket"].setsockopt(zmq.LINGER, 0)
            self.devices[device]["socket"].close()
        self.router_socket.setsockopt(zmq.LINGER, 0)
        self.router_socket.close()
        # Terminate the ZMQ context
        self.context.term()
        Node.__instance = None

    def genkeys(self, scheme, bit_length):
        if bit_length < 16:
            return "Minimum bit length is 16"
        if scheme == "Paillier":
            self.executor.submit(1, self.json_handler.genkeys, "Paillier", bit_length)
            return "Generating Paillier keys... Bit length: " + str(bit_length)
        elif scheme == "Damgard-Jurik":
            self.executor.submit(1, self.json_handler.genkeys, "Damgard-Jurik", bit_length)
            return "Generating Damgard-Jurik keys... Bit length: " + str(bit_length)
        elif scheme == "BFV":
            self.executor.submit(1, self.json_handler.genkeys, "BFV", bit_length)
            return "Generating BFV keys... Bit length is ignored"
        return "Invalid scheme X"

    def new_peer(self, peer, last_seen):
        if peer in self.devices:
            return f"Already knew {peer}"
        dealer_socket = self.context.socket(zmq.DEALER)
        dealer_socket.set_hwm(2000)
        dealer_socket.connect(f"tcp://{peer}:{self.port}")
        self.devices[peer] = {"socket": dealer_socket, "last_seen": last_seen}
        self.n = len(self.devices)
        print(f"Added {peer} to my network")
        return f"Added {peer} to the network"

    def discover_peers(self):
        print(f"Node {self.node_ip} (You) - Discovering peers on port {self.port}")
        sockets = []
        # Iterar sobre todas las direcciones IP posibles en la subred
        for i in range(1, 256):
            ip = f"192.168.1.{i}"
            if ip not in self.devices and ip != self.node_ip:
                # Crear un nuevo socket y tratar de conectar
                dealer_socket = self.context.socket(zmq.DEALER)
                print(f"Node {self.node_ip} (You) - Trying to connect to " + ip)
                dealer_socket.connect(f"tcp://{ip}:{self.port}")
                # Enviar un mensaje de descubrimiento
                dealer_socket.send_string(f"DISCOVER: Node {self.node_ip} is looking for peers")
                sockets.append(dealer_socket)
        # Se cierran todos, los que respondan se añadirán a la lista usando el método apropiado
        time.sleep(1)
        for socket in sockets:
            socket.setsockopt(zmq.LINGER, 0)
            socket.close()
        return "Discovering peers..."

    def start_intersection(self, device, scheme, type, rounds=1) -> str:
        if device in self.devices:
            return self.json_handler.start_intersection(device, scheme, type, rounds)
        return "Device not found - Have the peer send an ACK first"

    def launch_test(self, device) -> str:
        if device in self.devices:
            self.json_handler.test_launcher(device)
            return "Launching a massive test with " + device + " - Check logs"
        return "Device not found"

    def get_devices(self):
        return list(self.devices)

    def update_setup(self, domain, set_size) -> str:
        if not domain.isdigit() or not set_size.isdigit() or int(domain) < int(set_size):
            return "Invalid parameters"
        self.domain = int(domain)
        self.myData = set(random.sample(range(self.domain), int(set_size)))
        self.executor.submit(1, self.json_handler.genkeys, "BFV OPE", domain=self.domain)
        return "Setup updated - BFV is generating new keys and parameters in the background"

    def check_tasks(self) -> tuple[str, str]:
        total_node = self.executor.queue.qsize() + self.executor.tasks_in_progress
        total_handler = self.json_handler.executor.queue.qsize() + self.json_handler.executor.tasks_in_progress
        return (str(total_node) + " tasks running in the node" if
                total_node > 0 else "No tasks running in the node",
                str(total_handler) + " tasks running in the handler"
                if total_handler > 0 else "No tasks running in the handler")

    def send_message(self, peer, message):
        try:
            self.devices[peer]["socket"].send_json(message, zmq.NOBLOCK)
            print(f"Message sent to {peer}")
        except zmq.Again:
            print(f"Warning: HWM full - Message not sent to {peer} - Device is not consuming messages - Discarding it "
                  f"for the memory's sake")

    def commit(self):
        ledger: Ledger = self.ledgers[self.id]
        ledger.new_ld()
        self.P, self.S, self.dec_frag = PPVSS(ledger).distribute()
        ledger.P = self.P
        self.sync_all_nodes()

        # LDEI
        for node_id in range(ledger.n):
            if node_id != self.id:
                try:
                    response = requests.get(f"http://localhost:{DEFL_PORT}/node/verify_lde/{self.id}")
                    if not (response.status_code == 200):
                        print(
                            f"The LDEI verification {self.id} in node {node_id} was incorrect: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    print(f"Error in LDEI verification request at node {node_id}: {e}")

        return "Commit completed."

    def reveal(self):
        ledger: Ledger = self.ledgers[self.id]
        ledger.P = self.P
        # Uncomment to make all nodes honest.
        # ledger.P = self.P

        self.sync_all_nodes()

        # Verify polynomial
        for node_id in range(ledger.n):
            if node_id != self.id:
                try:
                    response = requests.get(f"http://localhost:{DEFL_PORT}/node/verify_polynomial/{node_id}")
                    if not (response.status_code == 200):
                        print(
                            f"The polynomial verification uploaded by node {node_id} was incorrect: {response.status_code}")
                        return "verify_polynomial operation failed", 400
                except requests.exceptions.RequestException as e:
                    print(f"Error in polynomial verification at node {node_id}: {e}")

        return "Reveal completed."

    def recovery(self, failed_nodes):

        ledger: Ledger = self.ledgers[self.id]

        self.__decrypt_fragment(failed_nodes)

        self.sync_all_nodes()

        # Check that the decrypted fragments are correct
        for node_id in range(ledger.n):
            try:
                failed_nodes_str = ','.join(map(str, failed_nodes))
                response = requests.get(
                    f"http://localhost:{DEFL_PORT}/node/{node_id}/verify_dleq/{self.id}?failed_nodes={failed_nodes_str}")

                if not (response.status_code == 200):
                    print(f"The DLEQ verification {self.id} at node {node_id} was incorrect: {response.status_code}")
                    return "verify_dleq operation failed", 400

            except requests.exceptions.RequestException as e:
                print(f"Error in DLEQ verification request at node {node_id}: {e}")

        return "Decryption correct"

    def reconstruction(self, failed_node, reco_parties):

        ledger: Ledger = self.ledgers[failed_node]
        for i, e in enumerate(reco_parties):
            reco_parties[i] = e

        sec = PPVSS(ledger).reconstruct(reco_parties)
        lista_sec = [int(x) for x in sec]
        return lista_sec

    def output(self):
        lista_int = [int(x) for x in self.S]
        return lista_int

    def verify_polynomial(self, poly_id):
        ledger: Ledger = self.ledgers[poly_id]
        # 2- Each node checks that the polynomial is correct.
        evaluations = [gf_multi_eval(ledger.P, [i % ledger.q], ledger.q, ZZ)[0] for i in
                       range(-ledger.l + 1, ledger.n + 1)]
        encrypted_fragments = [pow(ledger.pk[i], evaluations[i + ledger.l], ledger.p) for i in range(ledger.n)]
        for i in range(ledger.n):
            if not (encrypted_fragments[i] == ledger.encrypted_fragments[i]):
                print("The polynomial published by node {node_id} is not correct.")
                return False
        return True

    def verifie_LDEI(self, ledger_id):
        ledger: Ledger = self.ledgers[ledger_id]

        if not ledger.ld.verificar(ledger.q, ledger.p, ledger.pk, ledger.alpha, ledger.t + ledger.l,
                                   ledger.encrypted_fragments):
            print("The LDEI proof is not correct...")
            return False
        return True

    def verifie_DELQ(self, decrypt_id, failed_nodes):
        my_ledger: Ledger = self.ledgers[self.id]
        for node_id in failed_nodes:
            failed_ledger: Ledger = self.ledgers[node_id]

            g = [my_ledger.pk[decrypt_id], failed_ledger.encrypted_fragments[decrypt_id]]
            x = [my_ledger.h, failed_ledger.revealed_fragments[decrypt_id]]
            if not failed_ledger.get_dl()[decrypt_id].verificar(my_ledger.q, my_ledger.p, g, x):
                print("The DELQ proof is not correct...")
                return False
            return True

    def __decrypt_fragment(self, failed_nodes):
        my_ledger: Ledger = self.ledgers[self.id]
        invsk = pow(self.sk, -1, my_ledger.q)
        for node_id in failed_nodes:
            other_ledger: Ledger = self.ledgers[node_id]
            encrypted_fragment = other_ledger.encrypted_fragments[self.id]
            decrypted_fragment = pow(encrypted_fragment, invsk, my_ledger.p)
            other_ledger.revealed_fragments[self.id] = decrypted_fragment
            other_ledger.dl[self.id] = DLEQ()
            g = [self.pk, encrypted_fragment]
            x = [my_ledger.h, decrypted_fragment]
            other_ledger.dl[self.id].probar(my_ledger.q, my_ledger.p, g, x, invsk)

    def sync_all_nodes(self):
        try:
            response = requests.get(f"http://localhost:{DEFL_PORT}/api/sync_nodes")
            if response.status_code != 200:
                print(f"Error en la sincronización: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud de sincronización: {e}")

    def gossip_sync(self):
        for neighbor in self.neighbors:
            self.__sync_all_ledgers_with_neighbor(neighbor)

    def __sync_all_ledgers_with_neighbor(self, neighbor: "Node"):
        for i in range(len(self.ledgers)):
            self_ledger = self.ledgers[i]
            neighbor_ledger = neighbor.ledgers[i]

            if neighbor_ledger is None:
                continue

            if self_ledger is None:
                self.ledgers[i] = neighbor_ledger
            else:
                self.__sync_single_ledger(self_ledger, neighbor_ledger)

    def __sync_single_ledger(self, ledger: Ledger, neighbor_ledger: Ledger):
        if ledger.P == [] and neighbor_ledger.P != []:
            ledger.P = neighbor_ledger.P

        if not ledger.alpha and neighbor_ledger.alpha:
            ledger.alpha = neighbor_ledger.alpha

        if ledger.r == 0 and neighbor_ledger.r > 0:
            ledger.r = neighbor_ledger.r

        for i in range(len(ledger.pk)):
            if ledger.pk[i] == 0 and neighbor_ledger.pk[i] != 0:
                ledger.pk[i] = neighbor_ledger.pk[i]

        if not ledger.encrypted_fragments and neighbor_ledger.encrypted_fragments:
            ledger.encrypted_fragments = neighbor_ledger.encrypted_fragments

        for i in range(len(ledger.revealed_fragments)):
            if ledger.revealed_fragments[i] == 0 and neighbor_ledger.revealed_fragments[i] != 0:
                ledger.revealed_fragments[i] = neighbor_ledger.revealed_fragments[i]

        if ledger.ld is None and neighbor_ledger.ld is not None:
            ledger.ld = neighbor_ledger.ld

        for i in range(len(ledger.dl)):
            if ledger.dl[i] == 0 and neighbor_ledger.dl[i] != 0:
                ledger.dl[i] = neighbor_ledger.dl[i]

    def set_neighbors(self, neighbors):
        for neighbor in neighbors:
            if neighbor not in self.neighbors:
                self.neighbors.append(neighbor)

    def get_id(self):
        return self.id

    def get_neighbors(self) -> list["Node"]:
        return self.neighbors