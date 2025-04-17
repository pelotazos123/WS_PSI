import functools
import os

from flask import Flask, render_template, jsonify, request
from flask.views import MethodView

from Logs import Logs
from Network.Node import Node
from Network.collections import networking
from Network.collections.DbConstants import DEFL_PORT, print_banner
from Network.collections.networking import is_valid_ipv4, is_valid_ipv6
from Crypto.helpers.CryptoImplementation import CryptoImplementation
from Crypto.protocols.utils.utils import Utils
from Network.collections.DbConstants import DEFL_RNDMSIZE


def node_wrapper(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        node = Node.getinstance()
        if node is None:
            return jsonify({'status': 'The node is not running. Connect to the network first'})
        return func(node, *args, **kwargs)

    return wrapper


def create_app(test_config=None):
    print("The service is starting...")

    node_count = 0

    def create_node(port=DEFL_PORT):
        nonlocal node_count
        local_ip = networking.get_local_ip()

        k = 128 # Umbral

        q, p = Utils.findprime(k, DEFL_RNDMSIZE) # orden del subgrupo y modulo de operacion

        gen = Utils.generator(q) 
        h = pow(gen, 2, p) # generador del grupo

        n = 2 # Num nodes

        node = Node(node_count, local_ip, port, n, q, p, h)

        node_count += 1

        node.start()
        Logs.setup_logs(node.id, len(node.myData), node.domain)

    create_node()
    print_banner()

    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/metrics')
    def metrics():
        return render_template('metrics.html')

    @app.route('/api/devices', methods=['GET'])
    @node_wrapper
    def api_devices(node):
        return jsonify(node.get_devices())

    @app.route('/api/ping/<device>', methods=['POST'])
    @node_wrapper
    def api_ping(node, device):
        return jsonify({'status': node.ping_device(device)})

    @app.route('/api/port', methods=['GET'])
    @node_wrapper
    def api_port(node):
        if not node.running:
            return jsonify({'port': "Not connected to the network"})
        return jsonify({'port': node.port})

    @app.route('/api/disconnect', methods=['POST'])
    @node_wrapper
    def api_disconnect(node):
        node.stop()
        return jsonify({'status': 'Node destroyed'})

    @app.route('/api/connect', methods=['POST'])
    def api_connect():
        port = request.args.get('port')
        if Node.getinstance() is not None:
            return jsonify({'status': 'Node already connected'})
        if port is None or not port.isdigit():
            create_node()
        else:
            create_node(port)
        return jsonify({'status': 'Node connected using port ' + str(port) if port is not None else
        'Node connected using port ' + str(DEFL_PORT)})

    @app.route('/api/mykeys', methods=['GET'])
    @node_wrapper
    def api_pubkey(node):
        return (jsonify({'pubkeyN': str(node.json_handler.CSHandlers[CryptoImplementation.from_string("Paillier")].
                                        public_key.n),
                         'pubkeyG': str(node.json_handler.CSHandlers[CryptoImplementation.from_string("Paillier")].
                                        public_key.g),
                         'pubkeyNDJ': str(node.json_handler.
                                          CSHandlers[CryptoImplementation.from_string("DamgardJurik")].public_key.n),
                         'pubkeySDJ': str(node.json_handler.
                                          CSHandlers[CryptoImplementation.from_string("DamgardJurik")].public_key.s),
                         'pubkeyMDJ': str(node.json_handler.
                                          CSHandlers[CryptoImplementation.from_string("DamgardJurik")].public_key.m)}))

    @app.route('/api/intersection', methods=['POST'])
    @node_wrapper
    def api_intersection(node):
        data = request.get_json()
        device = data.get('device')
        scheme = data.get('scheme')
        type = data.get('type')
        rounds = data.get('rounds')
        if device is None or scheme is None or type is None:
            return jsonify({'status': 'Invalid parameters'})
        if rounds is None or not str(rounds).isdigit():
            rounds = 1
        return jsonify({'status': node.start_intersection(device, scheme, type, rounds)})

    @app.route('/api/dataset', methods=['GET'])
    @node_wrapper
    def api_dataset(node):
        return jsonify({'dataset': list(node.myData)})

    @app.route('/api/id', methods=['GET'])
    @node_wrapper
    def api_id(node):
        return jsonify({'id': node.node_ip})

    @app.route('/api/results', methods=['GET'])
    @node_wrapper
    def api_result(node):
        return jsonify({'result': node.results})

    @app.route('/api/genkeys', methods=['POST'])
    @node_wrapper
    def api_genkeys(node):
        scheme = request.args.get('scheme')
        bit_length = request.args.get('bit_length')
        if scheme is None:
            return jsonify({'status': 'Invalid parameters'})
        if not bit_length.isdigit():
            return jsonify({'status': 'Invalid bit length'})
        return jsonify({'status': node.genkeys(scheme, int(bit_length))})

    @app.route('/api/discover_peers', methods=['POST'])
    @node_wrapper
    def api_discover_peers(node):
        return jsonify({'status': node.discover_peers()})

    @app.route('/api/add', methods=['PUT'])
    @node_wrapper
    def api_add_peer(node):
        peer = request.args.get('peer')
        if peer is None:
            return jsonify({'status': 'Invalid parameters - No peer provided'})
        if is_valid_ipv4(peer) or is_valid_ipv6(peer):
            return jsonify({'status': node.new_peer(peer, "Not seen yet")})
        return jsonify({'status': 'Invalid IPv4 or IPv6 address'})

    @app.route('/api/logs', methods=['GET'])
    @node_wrapper
    def api_metrics(node):
        id = request.args.get('id')
        if id is not None:
            return Logs.get_logs(id)
        return Logs.get_logs(node.id)

    @app.route('/api/test', methods=['POST'])
    @node_wrapper
    def api_test(node):
        device = request.args.get('device')
        return jsonify({'status': node.launch_test(device)})

    @app.route('/api/setup', methods=['POST'])
    @node_wrapper
    def api_setup(node):
        domain = request.args.get('domain')
        set_size = request.args.get('set_size')
        if domain is None or set_size is None:
            return jsonify({'status': 'Invalid parameters'})
        res = node.update_setup(domain, set_size)
        if res == "Setup updated":
            Logs.setup_logs(node.id, set_size, domain)
        return jsonify({'status': res})

    @app.route('/api/check_connection', methods=['GET'])
    @node_wrapper
    def api_check_connection(node):
        return jsonify({'status': "Up and running!"})

    @app.route('/api/tasks', methods=['GET'])
    @node_wrapper
    def api_check_tasks(node):
        return jsonify({'status': node.check_tasks()})

    # ALBATROSS SECTION

    @app.route('/api/albatross', methods=['GET'])
    @node_wrapper
    def api_albatross(node):
        #Inicia secuencia de Albatross en nodo actual
        commit_duration = node.albatross.execute_commit_phase()
        reveal_duration = node.albatross.execute_reveal_phase()
        output_duration = node.albatross.handle_output_phase()
        
        #Se recupera el resultado final || Temporal lectura de ficheros
        with open('aleatoriedad_final.txt', 'r') as f:
            final_randomness = f.read()

        return jsonify({
            'status': 'Albatross executed successfully',
            'commit_time': commit_duration,
            'reveal_time': reveal_duration,
            'output_time': output_duration,
            'final_randomness': final_randomness
        })

    @app.route('/api/node/<int:node_id>/commit', methods=['GET'])
    @node_wrapper
    def api_node_commit(node, node_id):
        # Se asume que se verifica que node_id corresponda al nodo actual
        # o se consulta desde una lista interna de nodos, según la arquitectura.
        try:
            result = node.commit()  # Método commit() del nodo
            return jsonify({'status': result})
        except Exception as e:
            return jsonify({'status': str(e)}), 500

    @app.route('/api/node/<int:node_id>/reveal', methods=['GET'])
    @node_wrapper
    def api_node_reveal(node, node_id):
        try:
            result = node.reveal()  # Método reveal() del nodo
            return jsonify({'status': result})
        except Exception as e:
            return jsonify({'status': str(e)}), 500

    @app.route('/api/node/<int:node_id>/output', methods=['GET'])
    @node_wrapper
    def api_node_output(node, node_id):
        try:
            result = node.output()  # Método output() del nodo
            if result is False:
                return jsonify({'status': 'failure', 'node': node_id}), 500
            else:
                return jsonify({'result': result}), 200
        except Exception as e:
            return jsonify({'status': str(e)}), 500

    @app.route('/api/node/<int:node_id>/recovery', methods=['GET'])
    @node_wrapper
    def api_node_recovery(node, node_id):
        try:
            failed_nodes = request.args.get('failed_nodes', '').split(',')
            failed_nodes = [int(x) for x in failed_nodes if x]
            result = node.recovery(failed_nodes)  # Método recovery() del nodo
            if result is False:
                return jsonify({'status': 'failure', 'node': node_id}), 500
            else:
                return jsonify({'result': result}), 200
        except Exception as e:
            return jsonify({'status': str(e)}), 500

    @app.route('/api/node/<int:node_id>/reconstruction/<int:reco_id>', methods=['GET'])
    @node_wrapper
    def api_node_reconstruction(node, node_id, reco_id):
        try:
            reco_parties = request.args.get('reco_parties', '').split(',')
            reco_parties = [int(x) for x in reco_parties if x]
            result = node.reconstruction(node_id, reco_parties)  # Método reconstruction() del nodo
            if result is False:
                return jsonify({'status': 'failure', 'node': node_id}), 500
            else:
                return jsonify({'result': result}), 200
        except Exception as e:
            return jsonify({'status': str(e)}), 500

    @app.route('/api/node/<int:node_id>/decrypt_fragment', methods=['GET'])
    @node_wrapper
    def api_node_decrypt_fragment(node, node_id):
        try:
            i = request.args.get('i')
            if i is None:
                return jsonify({"status": "error", "message": "Parameter 'i' is required"}), 400
            i = int(i)
            node.decrypt_fragment(i)  # Método decrypt_fragment() del nodo
            return jsonify({"status": "success", "message": f"Fragment {i} decrypted and uploaded to ledger."})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/node/<int:node_id>/verify_lde/<int:ledger_id>', methods=['GET'])
    @node_wrapper
    def api_node_verify_lde(node, node_id, ledger_id):
        try:
            if node.verifie_LDEI(ledger_id):
                return jsonify({"status": "success", "message": "LDEI verified successfully"}), 200
            else:
                return jsonify({"status": "error", "message": "Incorrect LDEI"}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/node/<int:node_id>/verify_polynomial/<int:poly_id>', methods=['GET'])
    @node_wrapper
    def api_node_verify_polynomial(node, node_id, poly_id):
        try:
            if node.verify_polynomial(poly_id):
                return jsonify({"status": "success", "message": "Polynomial verified successfully"}), 200
            else:
                return jsonify({"status": "error", "message": "Incorrect Polynomial"}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/node/<int:node_id>/verify_dleq/<int:ledger_id>', methods=['GET'])
    @node_wrapper
    def api_node_verify_dleq(node, node_id, ledger_id):
        try:
            failed_nodes = request.args.get('failed_nodes', '').split(',')
            failed_nodes = [int(x) for x in failed_nodes if x]
            if node.verifie_DELQ(ledger_id, failed_nodes):
                return jsonify({"status": "success", "message": "DLEQ verified successfully"}), 200
            else:
                return jsonify({"status": "error", "message": "Incorrect DLEQ"}), 400
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/sync_nodes', methods=['GET'])
    def api_sync_nodes():
        try:
            # Se llama al método de sincronización de la red
            from Network.collections.networking import networking
            networking.sync_nodes()  # o el método correspondiente en tu implementación
            return jsonify({"status": "success", "message": "Synchronization completed"}), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    return app


    # noinspection PyMethodMayBeStatic
    # To be able to use appropriate API methods, GET for status and POST for connect/disconnect
    class FirebaseAPI(MethodView):
        def get(self):
            if Logs.default_app is None:
                return jsonify({'status': 'Firebase not connected - The application will not log data to Firebase'})
            return jsonify({'status': 'Firebase connected'})

        def post(self):
            action = request.args.get('action')
            if action == 'connect':
                return jsonify({'status': Logs.connect_firebase()})
            elif action == 'disconnect':
                return jsonify({'status': Logs.disconnect_firebase()})

    app.add_url_rule('/api/firebase', view_func=FirebaseAPI.as_view('firebase_api'))

    return app
