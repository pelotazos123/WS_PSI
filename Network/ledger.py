from Crypto.generators.Albatross.Proofs.LDEI import LDEI
from Crypto.generators.Albatross.Proofs.DLEQ import DLEQ

class Ledger:
    def __init__(self, n, q, p, h, pk=None):
        self.n = n
        self.t = round(n // 3) 
        self.l = n - (2 * self.t) 
        self.q = q  
        self.p = p  
        self.h = h 

        self.pk = [0] * n

        self.P = []
        self.alpha = []
        self.r = 0  
        self.encrypted_fragments = []  
        self.revealed_fragments = [0] * n  
        self.ld = None  
        self.dl: list[DLEQ] = [0] * self.n


    def new_ld(self):
        self.ld = LDEI()
        
    def get_n(self):
        return self.n

    def get_t(self):
        return self.t

    def get_l(self):
        return self.l

    def get_q(self):
        return self.q

    def get_p(self):
        return self.p

    def get_h(self):
        return self.h

    def get_pk(self):
        return self.pk

    def get_P(self):
        return self.P

    def get_alpha(self):
        return self.alpha


    def get_encrypted_fragments(self):
        return self.encrypted_fragments

    def get_revealed_fragments(self):
        return self.revealed_fragments

    def get_ld(self):
        return self.ld

    def get_dl(self):
        return self.dl

 