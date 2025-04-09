import random
from time import sleep
from sympy.polys.domains import ZZ  
from sympy.polys.galoistools import gf_multi_eval
from ..Albatross.Proofs.LDEI import LDEI
from ....Network.ledger import Ledger

class PPVSS:
    def __init__(self, ledger: Ledger):
        """Initializes PPVSS with a Ledger instance."""
        self.__ledger: Ledger = ledger

    def distribute(self):
        """Distributes the secret by creating a polynomial, evaluating it, and uploading the encrypted fragments to the ledger."""
        
        q = self.__ledger.get_q()
        p = self.__ledger.get_p()
        n = self.__ledger.get_n()
        l = self.__ledger.get_l()
        pk = self.__ledger.get_pk() 

        deg = self.__ledger.get_t() + l 
        P = [random.randint(0, q - 1) for _ in range(deg + 1)]
        evaluation = [gf_multi_eval(P, [i % q], q, ZZ)[0] for i in range(-l + 1, n + 1)]
        S = [sec for sec in evaluation[:l]]
        fragments = [x for x in evaluation if x not in S]
        self.__ledger.encrypted_fragments = [pow(pk[i], evaluation[i + l], p) for i in range(n)]

        self.__ledger.alpha = [(i + 1) % q for i in range(n)]
        self.__ledger.get_ld().probar(q, p, pk, self.__ledger.alpha, deg, self.__ledger.encrypted_fragments, P)

        return P, S, fragments

    def __lambdas(self, reco_parties, t):
        """Calculates the lambda coefficients for secret reconstruction."""
        
        lambs = [[0] * self.__ledger.l for _ in range(t)]
        q = self.__ledger.q

        for j in range(self.__ledger.l):
            for i in range(t):
                num = 1
                den = 1
                for m in range(t):
                    if m != i:
                        num_step = (-j - reco_parties[m]) % q
                        den_step = (reco_parties[i] - reco_parties[m]) % q
                        num = (num * num_step) % q
                        den = (den * den_step) % q
                invden = pow(den, -1, q)
                mu = (num * invden) % q
                lambs[i][j] = mu
                
        return lambs

    def reconstruct(self, reco_parties):
        """Reconstructs the secret using the ledger and performs a local LDEI verification."""
        reco_parties = [x + 1 for x in reco_parties]
        print("reco_parties: ", reco_parties)
        sigtilde = [self.__ledger.revealed_fragments[party_id-1] for party_id in reco_parties] # Pueden estar mal colocados

        r = self.__ledger.n - self.__ledger.t
        l = self.__ledger.l
        p = self.__ledger.p
        q = self.__ledger.q
        t = self.__ledger.n - self.__ledger.t

        

        lambs = self.__lambdas(reco_parties, t)
        Sec = [0] * l
        for j in range(l):
            Sec[l-j-1] = 1

            for i in range(t):
                tmp = pow(sigtilde[i], lambs[i][j], p)
                Sec[l-j-1] = (Sec[l-j-1] * tmp) % p

        # Operaciones mod q
        alphaverif = []
        for j in range(l):
            alphaverif.append(j-l+1)

        for j in range(l, r+l):
            alphaverif.append(reco_parties[j-l])

        # Operaciones mod p
        xverif = []
        for j in range(l):
            xverif.append(Sec[j])

        for j in range(l, r+l):
            xverif.append(sigtilde[j-l])

        print("xverif: ", len(xverif))

        # Verificación LDEI local
        if not LDEI.localldei(q, p, alphaverif, self.__ledger.t + l, xverif, r + l):
            print("La verificación LDEI local falló.")
            return False

        return Sec
