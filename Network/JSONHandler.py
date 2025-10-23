import json
import random
import time
import requests

from Crypto.handlers.CAOPEHandler import CAOPEHandler
from Crypto.handlers.DomainPSIHandler import DomainPSIHandler
from Crypto.handlers.OPEHandler import OPEHandler
from Crypto.helpers.BFVHelper import BFVHelper
from Crypto.helpers.CryptoImplementation import CryptoImplementation
from Crypto.helpers.DamgardJurikHandler import DamgardJurikHelper
from Crypto.helpers.PaillierHandler import PaillierHelper
from Logs import Logs
from Logs.Logs import ThreadData
from Network.PriorityExecutor import PriorityExecutor
from Network.collections.DbConstants import VERSION, TEST_ROUNDS, DEFL_PORT
from Crypto.handlers.NumericKPhaseHandler import NumericKPhaseHandler


def random_albatross():
    try:
        r = requests.get(f"http://localhost:{DEFL_PORT}/api/albatross")

        if r.status_code == 200:
            data = r.json()
            shared_randomness = data['final_randomness']
            print("Aleatoriedad compartida obtenida:", shared_randomness)
            return shared_randomness
        else:
            print("Error al obtener la aleatoriedad compartida:", r.status_code)

    except Exception as e:
        print("Error en la llamada a ALBATROSS:", e)

def random_spurt():
    # TODO
    return "TODO"

def random_herb():
    # TODO
    return "TODO"

def random_scrape():
    # TODO
    return "TODO"

# Priorities
# 0: Intersection first step
# 1: Intersection second step
# 2: Intersection final step
# 1 and 2 will be executed first to stop consuming memory on the queue
class JSONHandler:
    def __init__(self, id, my_data, domain, devices, results, new_peer_function):
        self.CSHandlers = {
            CryptoImplementation("Paillier", "Paillier OPE", "Paillier_OPE",
                                 "Paillier PSI-CA OPE"): PaillierHelper(), # strings to choose protocol to be used

            CryptoImplementation("DamgardJurik", "Damgard-Jurik", "DamgardJurik OPE",
                                 "Damgard-Jurik_OPE", "Damgard-Jurik OPE", "DamgardJurik PSI-CA OPE",
                                 "Damgard-Jurik PSI-CA OPE"): DamgardJurikHelper(),

            CryptoImplementation("BFV", "BFV_OPE", "BFV OPE"): BFVHelper()
        }
        self.OPEHandler = OPEHandler(id, my_data, domain, devices, results)
        self.CAOPEHandler = CAOPEHandler(id, my_data, domain, devices, results)
        self.domainPSIHandler = DomainPSIHandler(id, my_data, domain, devices, results)
        self.id = id
        self.devices = devices
        self.executor = PriorityExecutor(max_workers=10)
        self.new_peer = new_peer_function
        self.generator = "albatross"

    def test_launcher(self, device):
        cs_handlers = self.CSHandlers.values()
        for _ in range(TEST_ROUNDS):
            for cs in cs_handlers:
                self.executor.submit(0, self.domainPSIHandler.intersection_first_step, device, cs)
                self.executor.submit(0, self.OPEHandler.intersection_first_step, device, cs)
                self.executor.submit(0, self.CAOPEHandler.intersection_first_step, device, cs)

    def genkeys(self, cs, bit_length=None, domain=None):
        start_time = time.time()
        thread_data = ThreadData()
        Logs.start_logging(thread_data)
        if domain is not None:
            self.CSHandlers[CryptoImplementation.from_string(cs)].generate_keys(bit_length=bit_length, domain=domain)
        else:
            self.CSHandlers[CryptoImplementation.from_string(cs)].generate_keys(bit_length=bit_length)
        end_time = time.time()
        Logs.stop_logging(thread_data)
        print("Key generation - " + cs + " - Time: " + str(end_time - start_time) + "s")
        Logs.log_activity(thread_data, "GENKEYS_" + cs + "-" + str(bit_length), end_time - start_time, VERSION, self.id)

    def check_generator(self):
        match self.generator:
            case 'albatross':
                return random_albatross()
            case 'spurt':
                return random_spurt()
            case 'scrape':
                return random_scrape()
            case 'herb':
                print("random")
                return random_herb()
            case _:
                return random_albatross()

    def start_intersection(self, device, scheme, type, rounds) -> str:
        crypto_impl = CryptoImplementation.from_string(scheme)
        if crypto_impl in self.CSHandlers:
            cs = self.CSHandlers[crypto_impl]
            if type == "OPE":
                for _ in range(int(rounds)):
                    self.executor.submit(0, self.OPEHandler.intersection_first_step, device, cs)
            elif type == "PSI-CA" and cs.imp_name != "BFV":
                for _ in range(int(rounds)):
                    self.executor.submit(0, self.CAOPEHandler.intersection_first_step, device, cs)
            elif type == "PSI-Domain":
                for _ in range(int(rounds)):
                    self.executor.submit(0, self.domainPSIHandler.intersection_first_step, device, cs)
            else:
                return "Invalid type: " + type if cs.imp_name != "BFV" else "BFV does not support PSI-CA... yet"
            return ("Intersection with " + device + " - " + scheme + " - " + type + " - Rounds: " + str(rounds) +
                    " - Task started, check logs")
        return "Invalid scheme: " + scheme

    def handle_message(self, message):
        try:
            message = json.loads(message)
            print(f"Node {self.id} (You) received: {message}")


            print("NUMERIC_KPHASE_START"==message['step'])
            print(message['k'])
            print(message['step'])

            if message['peer'] not in self.devices:
                print("peer")
                self.new_peer(message['peer'], time.strftime("%H:%M:%S", time.localtime()))
            if message['step'] == "2":
                print("s2")
                self.handle_intersection_second_step(message)
                
            print("s3")
            ##################################################################################    

            if message['step'] == "NUMERIC_KPHASE_START":
                print("1")
                value = random.uniform(0, 50)  
                print("2")
                shares = self.numericKPhaseHandler.local_compute(value)
                print("3")
                print(f"Local shares computed: {shares}")
                response = {
                    "step": "NUMERIC_KPHASE_RESULT",
                    "peer": self.id,
                    "data": shares
                }
                collector = message["collector"]
                self.devices[collector]["socket"].send_json(response)
            
            if message['step'] == "NUMERIC_KPHASE_RESULT":
                peer_data = message["data"]
                if "numeric_kphase_results" not in self.results:
                    self.results["numeric_kphase_results"] = []
                self.results["numeric_kphase_results"].extend(peer_data)

                if len(self.results["numeric_kphase_results"]) >= len(self.devices):
                    final = self.numericKPhaseHandler.aggregate_results(
                        self.results["numeric_kphase_results"]
                    )
                    self.results["final_numeric_kphase"] = final
                    print(f"Final regression result: {final}")


            elif message['step'] == "F":
                self.handle_intersection_final_step(message)

            print("4")
        except json.JSONDecodeError:
            print("Received message is not a valid JSON.")

    def handle_intersection_second_step(self, message):
        crypto_impl = CryptoImplementation.from_string(message['implementation'])
        if crypto_impl in self.CSHandlers:
            cs = self.CSHandlers[crypto_impl]
            if "PSI-CA" in message['implementation']:
                self.executor.submit(1, self.CAOPEHandler.intersection_second_step, message['peer'],
                                     cs, message['data'], message['pubkey'])
            elif "OPE" in message['implementation']:
                self.executor.submit(1, self.OPEHandler.intersection_second_step, message['peer'], cs,
                                     message['data'], message['pubkey'])
            else:
                self.executor.submit(1, self.domainPSIHandler.intersection_second_step, message['peer'], cs,
                                     message['data'], message['pubkey'])
        else:
            Exception("Invalid scheme: " + message['implementation'])

    def handle_intersection_final_step(self, message):
        crypto_impl = CryptoImplementation.from_string(message['implementation'])
        if crypto_impl in self.CSHandlers:
            cs = self.CSHandlers[crypto_impl]
            if "PSI-CA" in message['implementation']:
                self.executor.submit(2, self.CAOPEHandler.intersection_final_step, message['peer'], cs,
                                     message['data'])
            elif "OPE" in message['implementation']:
                self.executor.submit(2, self.OPEHandler.intersection_final_step, message['peer'], cs,
                                     message['data'])
            else:
                self.executor.submit(2, self.domainPSIHandler.intersection_final_step, message['peer'], cs,
                                     message['data'])
        else:
            Exception("Invalid scheme: " + message['implementation'])
