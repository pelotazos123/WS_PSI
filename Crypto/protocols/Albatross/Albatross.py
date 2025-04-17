import random
import threading 
import time
import numpy as np
import requests
import sys

from ..utils.utils import Utils


class ALBATROSS:
    def __init__(self, h, q, p): 
        """Initializes ALBATROSS protocol"""
        self.__num_participants = 2
        self.__t = self.__num_participants // 3
        self.__successful_commit_ids = set()
        self.__successful_reveal_ids = set()
        self.__successful_recovery_ids = set()
        self.h = h
        self.q = q
        self.p = p
        self.__T = []

    def __request_commit(self, node_id):
        """Sends a commit request to the node and adds the node to successful commits if successful."""
        try:
            response = requests.get(f"http://localhost:5000/node/{node_id}/commit")
            if (response.status_code == 200) and (len(self.__successful_commit_ids) < (self.__num_participants - self.__t)):
                self.__successful_commit_ids.add(node_id)
                print(f"Commit successful on node {node_id}: {response.text}")
            else:
                print(f"Commit failed on node {node_id}: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error during commit on node {node_id}: {e}")

    def __request_reveal(self, node_id):
        """Sends a reveal request to the node and adds the node to successful reveals if successful."""
        try:
            response = requests.get(f"http://localhost:5000/node/{node_id}/reveal")
            if response.status_code == 200:
                self.__successful_reveal_ids.add(node_id)
                print(f"Reveal successful on node {node_id}: {response}")
            else:
                print(f"Reveal failed on node {node_id}: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error during reveal on node {node_id}: {e}")

    def __request_output(self, node_id):
        """Sends a request to extract randomness from the node and appends the result."""
        try:
            response = requests.get(f"http://localhost:5000/node/{node_id}/output")
            if response.status_code == 200:
                json_response = response.json()
                decoded_response = json_response.get('result', [])
                numbers = [int(x) for x in decoded_response]
                self.__T.append(numbers)
                print("Number of secrets post-add:", len(self.__T))
                print(f"Randomness extraction successful on node {node_id}")
            else:
                print(f"Output request failed on node {node_id}: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error during output request on node {node_id}: {e}")

    def __request_recovery(self, node_id, failed_nodes):
        """Sends a recovery request to the node in case some nodes failed."""
        try:
            failed_nodes_str = ','.join(map(str, failed_nodes))
            response = requests.get(f"http://localhost:5000/node/{node_id}/recovery?failed_nodes={failed_nodes_str}")
            if response.status_code == 200:
                self.__successful_recovery_ids.add(node_id)
                print(f"Recovery successful on node {node_id}")
            else:
                print(f"Recovery failed on node {node_id}: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error during recovery request on node {node_id}: {e}")
    
    def __request_reconstruction(self, reco_id, node_id, reco_parties):
        """Sends a reconstruction request to the node with the given reconstruction parties."""
        try:
            reco_part = ','.join(map(str, reco_parties))
            response = requests.get(f"http://localhost:5000/node/{reco_id}/reconstruction/{node_id}?reco_parties={reco_part}")
            if response.status_code == 200:
                
                json_response = response.json()
                decoded_response = json_response.get('result', [])
                numbers = [int(x) for x in decoded_response]
                self.__T.append(numbers)
                print("Number of secrets post-add:", len(self.__T))



                print(f"Reconstruction successful for node {node_id}")
            else:
                print(f"Reconstruction failed for node {node_id}: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error during reconstruction request on node {node_id}: {e}")




    def execute_commit_phase(self):
        """Executes the commit phase by sending commit requests to all participants."""
        start_time = time.time()
        threads = []
        print("Executing commit requests...")
        for i in range(self.__num_participants):
            thread = threading.Thread(target=self.__request_commit, args=(i,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        end_time = time.time()
        return end_time - start_time

    def execute_reveal_phase(self):
        """Executes the reveal phase by sending reveal requests to all successfully committed nodes."""
        start_time = time.time()
        threads = []
        print("Executing reveal requests...")
        for node_id in self.__successful_commit_ids:
            thread = threading.Thread(target=self.__request_reveal, args=(node_id,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        end_time = time.time()
        return end_time - start_time

    def handle_output_phase(self):
        """Handles the output phase by either processing the output or executing the recovery phase."""
        start_time = time.time()
        if len(self.__successful_reveal_ids) == (self.__num_participants - self.__t):
            print("All reveals were successful.")
            self.__process_output()
            end_time = time.time()
            return end_time - start_time
        else:
            print("Some reveals failed. Proceeding with alternative action.")
            self.__execute_recovery_phase()
            end_time = time.time()
            return end_time - start_time

    def __process_output(self):
        """Processes the output by sending output requests to all successfully revealed nodes."""
        threads = []
        for node_id in self.__successful_reveal_ids:
            thread = threading.Thread(target=self.__request_output, args=(node_id,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        self.__process_final_output()

    def __process_final_output(self):
        """Processes the final output by reconstructing the secret using Vandermonde matrix and randomness."""
        w = Utils.rootunity(len(self.__T[0]), self.q) 
        t = self.__num_participants // 3
        l = self.__num_participants - 2 * t
        matriz_vander = self.__crear_matriz_vandermonde(w, l, t)
        print("Vandermonde matrix size:", matriz_vander.shape)

        matriz_T = np.array(self.__T)
        print("Matrix T size:", matriz_T.shape)

        matriz_T_transpuesta = matriz_T.T
        print("Transposed T matrix size:", matriz_T_transpuesta.shape)

        sys.set_int_max_str_digits(10_000_000)
        aleatoriedad_final = self.__multiplicar_matrices(matriz_vander, matriz_T_transpuesta)
        print("Secret reconstruction completed.")
        with open('aleatoriedad_final.txt', 'w') as archivo:
            archivo.write(str(aleatoriedad_final))  
        return

    def __execute_recovery_phase(self):
        """Executes the recovery phase to recover failed nodes."""
        threads = []
        failed_nodes = self.__successful_commit_ids - self.__successful_reveal_ids 

        for node_id in range(self.__num_participants):
            thread = threading.Thread(target=self.__request_recovery, args=(node_id, failed_nodes))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        if len(self.__successful_recovery_ids) >= (self.__num_participants - self.__t):
            print("Proceeding with secret reconstruction.")
            self.__execute_reconstruction_phase(failed_nodes)
        else:
            print("Cannot reconstruct secret, insufficient number of well-intentioned participants.")
            exit(-1)

    def __execute_reconstruction_phase(self, failed_nodes):
        """Executes the reconstruction phase by gathering output from successfully revealed nodes and calculating the final output."""
        threads = []
        for node_id in self.__successful_reveal_ids:
            thread = threading.Thread(target=self.__request_output, args=(node_id,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()

        # Convert the matrix to h^s elements
        print("Number of secrets:", len(self.__T))

        for lista in self.__T:
            for i in range(len(lista)):
                lista[i] = pow(self.h, lista[i], self.p)
        
        t = self.__num_participants // 3
        l = self.__num_participants - 2 * t
        r = self.__num_participants - t
        threads = []
        participantes = list(range(self.__num_participants))
        for node_id in failed_nodes:
            # Remove the node to be reconstructed
            if node_id in participantes:
                participantes.remove(node_id)

            # Choose reconstruction parties
            subgrupo = random.sample(participantes, r)

            thread = threading.Thread(target=self.__request_reconstruction, args=(node_id, subgrupo[0], subgrupo))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()

       
        # Create Vandermonde matrix with w.
        w = Utils.rootunity(len(self.__T[0]), self.q)
        
        matriz_vander = self.__crear_matriz_vandermonde(w, l, t)
        print("Vandermonde matrix size:", matriz_vander.shape)

        matriz_T = np.array(self.__T)
        print("Matrix T size:", matriz_T.shape)

        # Transpose matrix T
        matriz_T_transpuesta = matriz_T.T
        print("Transposed T matrix size:", matriz_T_transpuesta.shape)

        # Calculate output by multiplying M * T in the exponent.
        aleatoriedad_final = self.__multiplicar_matrices(matriz_vander, matriz_T_transpuesta)
        aleatoriedad_final = self.__multiplicar_matrices(matriz_vander, matriz_T_transpuesta)

        # Guardar el contenido de aleatoriedad_final en un archivo .txt
        with open('aleatoriedad_final.txt', 'w') as archivo:
            archivo.write(str(aleatoriedad_final))

        print("Secret reconstruction completed.")

    def __crear_matriz_vandermonde(self, omega, l, t):
        """
        Creates a Vandermonde matrix of size (l, t + l).
        """
        n_columnas = t + l
        return np.array([[omega**j for j in range(n_columnas)] for i in range(l)])

    def __multiplicar_matrices(self, matriz_a, matriz_b):
        """
        Multiplies two matrices of the same size.
        """
        return np.multiply(matriz_a, matriz_b)
