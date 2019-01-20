#
# Copyright (c) 2017, Stephanie Wehner and Axel Dahlberg
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. All advertising materials mentioning features or use of this software
#    must display the following acknowledgement:
#    This product includes software developed by Stephanie Wehner, QuTech.
# 4. Neither the name of the QuTech organization nor the
#    names of its contributors may be used to endorse or promote products
#    derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import argparse
import math
import random
import sys

from scipy.linalg import toeplitz
from numpy import matmul

from SimulaQron.cqc.pythonLib.cqc import CQCConnection
import communication
import authentication as auth

import utils

#####################################################################################################
#
# main
#


class Receiver(object):
    def __init__(self, name="Bob", correctness_param=2, security_param=1):
        # CQCConnection.__init__(self, name)
        self.cqc = None
        self.name = name
        self.correctness_param = correctness_param
        self.security_param = security_param

        self.skey = auth.generate_private_key()
        self.pkey = auth.publish_public_key(self.name, self.skey)
        self.sender = ''
        self.sender_pkey = ''

        self.msg = ''
        self.n = 0
        self.N = 0

        self.raw_key = []
        self.basis_list = []
        self.sifted_key = []
        self.sifted_basis = []

        self.error_estimation = 0.0

    def receive(self, sender='Alice'):
        with CQCConnection(self.name) as self.cqc:
            self.cqc.closeClassicalServer()
            self.sender = sender
            self.sender_pkey = auth.get_public_key(sender)

            self.n = int(communication.receive_message(self.cqc, self.sender_pkey))  # TODO: change to receive parameters
            self.N = math.ceil((4 + self.correctness_param) * self.n) + 25
            self._receive_qubits()
            self._perform_basis_sift()
            can_continue = self._perform_error_estimation()
            if not can_continue:
                print('Not enough min entropy :(')
                return
            self._perform_error_correction()
            self._perform_privacy_amplification()
            cyphertext = communication.receive_binary_list(self.cqc, self.sender_pkey)
            plaintext = self._decrypt(cyphertext)
            print(plaintext)
            f = open(self.name, 'wb')
            f.write(plaintext)
            f.close()

    def _receive_qubits(self):
        # print("Receiving {} qubits...".format(self.N))
        for i in range(0, self.N):

            # Receive qubit from Alice (via Eve)
            q = self.cqc.recvQubit()

            # Choose a random basis
            chosen_basis = random.randint(0, 1)
            self.basis_list.append(chosen_basis)
            if chosen_basis == 1:
                q.H()

            # Retrieve key bit
            k = q.measure()
            self.raw_key.append(k)
            communication.send_message(self.cqc, self.sender, self.skey, 'ok')

        communication.send_message(self.cqc, self.sender, self.skey, 'DONE')

    def _perform_basis_sift(self):
        print("Performing Basis sift...", end='\r')

        receiver_basis = communication.receive_binary_list(self.cqc, self.sender_pkey)
        communication.send_binary_list(self.cqc, self.sender, self.skey, self.basis_list)

        diff_basis = []
        for i in range(0, len(receiver_basis)):
            if receiver_basis[i] != self.basis_list[i]:
                diff_basis.append(i)

        self.sifted_key = utils.remove_indices(self.raw_key, diff_basis)
        self.sifted_basis = utils.remove_indices(self.basis_list, diff_basis)
        print("Performing Basis sift... Done!")

    def _perform_error_estimation(self):
        print('Performing error estimation...', end='\r')

        error_estimation_indices = communication.receive_list(self.cqc, self.sender_pkey)
        sender_key_part = communication.receive_binary_list(self.cqc, self.sender_pkey)

        num_errors = 0.0
        key_part = []
        for i in range(0, len(error_estimation_indices)):
            key_part.append(self.sifted_key[error_estimation_indices[i]])
            if sender_key_part[i] != key_part[i]:
                num_errors += 1.0

        communication.send_binary_list(self.cqc, self.sender, self.skey, key_part)

        self.error_estimation = num_errors / len(key_part)
        print('B Performing error estimation... Done!')
        print('B Error rate = {}'.format(self.error_estimation))

        error_estimation_indices.sort()
        self.sifted_key = utils.remove_indices(self.sifted_key, error_estimation_indices)
        remaining_bits = len(self.sifted_key)
        min_entropy = remaining_bits * (1 - utils.h(self.error_estimation))
        max_key = min_entropy - 2 * utils.log(1/self.security_param, 2) - 1

        return self.n <= max_key

    def _perform_error_correction(self):
        if self.error_estimation == 0:
            return
        self._cascade()

    def _cascade(self):
        n = math.ceil(0.73 / self.error_estimation)
        iterations = [[]]

        # 1st iteration
        for i in range(0, len(self.sifted_key), n):
            iterations[0].append(list(range(i, min(i + n, len(self.sifted_key) - 1))))

        parities = utils.calculate_parities(self.sifted_key, iterations[0])
        alice_parities = communication.receive_binary_list(self.cqc, self.sender_pkey)

        for i in range(0, len(alice_parities)):
            if parities[i] != alice_parities[i]:
                communication.send_message(self.cqc, self.sender, self.skey, i)
                self._binary(iterations[0][i])
        communication.send_message(self.cqc, self.sender, self.skey, 'ALL DONE')

        # nth iteration
        for iter_num in range(1, 4):
            n = 2 * n
            iterations.append([])
            temp_indices = communication.receive_list(self.cqc, self.sender_pkey)
            for i in range(0, len(self.sifted_key), n):
                iterations[iter_num].append(temp_indices[i:min(i + n, len(self.sifted_key) - 1)])
            parities = utils.calculate_parities(self.sifted_key, iterations[iter_num])
            alice_parities = communication.receive_binary_list(self.cqc, self.sender_pkey)
            for i in range(0, len(alice_parities)):
                if parities[i] != alice_parities[i]:
                    correcting_block = i
                    for j in range(0, iter_num + 1):
                        communication.send_message(self.cqc, self.sender, self.skey, [iter_num - j, correcting_block])
                        corrected_index = self._binary(iterations[iter_num - j][correcting_block])
                        if iter_num - j - 1 >= 0:
                            correcting_block = utils.get_num_block_with_index(iterations[iter_num - j - 1], corrected_index)
            communication.send_message(self.cqc, self.sender, self.skey, 'ALL DONE')

    def _binary(self, block):
        alice_first_half_par = int(communication.receive_message(self.cqc, self.sender_pkey))

        first_half_size = math.ceil(len(block) / 2.0)
        first_half_par = utils.calculate_parity(self.sifted_key, block[:first_half_size])

        if first_half_par != alice_first_half_par:
            if first_half_size == 1:
                self.sifted_key[block[0]] = (self.sifted_key[block[0]] + 1) % 2
                communication.send_message(self.cqc, self.sender, self.skey, 'DONE')
                return block[0]
            else:
                communication.send_message(self.cqc, self.sender, self.skey, 0)
                return self._binary(block[:first_half_size])
        else:
            if len(block) - first_half_size == 1:
                self.sifted_key[block[-1]] = (self.sifted_key[block[-1]] + 1) % 2
                communication.send_message(self.cqc, self.sender, self.skey, 'DONE')
                return block[-1]
            else:
                communication.send_message(self.cqc, self.sender, self.skey, 1)
                return self._binary(block[first_half_size:])

    def _perform_privacy_amplification(self):
        seed = communication.receive_binary_list(self.cqc, self.sender_pkey)
        seed_col = seed[:self.n]
        seed_row = seed[self.n:]

        self.final_key = matmul(toeplitz(seed_col, seed_row), self.sifted_key)

    def _decrypt(self, cyphertext):
        plaintext = []
        for i in range(0, len(cyphertext)):
            plaintext.append((cyphertext[i] + self.final_key[i]) % 2)
        return communication.bitlist_to_bytes(plaintext)


"""def main():

    skey = auth.generate_private_key()
    auth.publish_public_key('Bob', skey)
    alice_pkey = auth.get_public_key('Alice')

    basis_list = []
    raw_key = []

    with CQCConnection("Bob") as Bob:
        # msg = communication.binary_to_dict(Bob.recvClassical())
        # auth.verify(alice_pkey, msg)
        msg = communication.receive_message(Bob,alice_pkey)
        n = int(msg)
        N = math.ceil((n + CORRECTNESS_PARAMETER)*4)
        print(N)

        for i in range(0, N):

            # Receive qubit from Alice (via Eve)
            q = Bob.recvQubit()

            # Choose a random basis
            chosen_basis = random.randint(0, 1)
            basis_list.append(chosen_basis)
            if chosen_basis == 1:
                q.H()

            # Retrieve key bit
            k = q.measure()
            raw_key.append(str(k))

        # Bob.sendClassical('Alice', communication.dict_to_binary(auth.sign(skey, 'DONE')))
        communication.send_message(Bob, 'Alice', skey, 'DONE')
        """


def main():
    bob = Receiver()
    bob.receive()

    """
    skey = auth.generate_private_key()
    auth.publish_public_key('Bob', skey)
    alice_pkey = auth.get_public_key('Alice')

    basis_list = []
    raw_key = []

    # Initialize the connection
    with CQCConnection("Bob") as Bob:
        Bob.closeClassicalServer()

        msg = communication.receive_message(Bob,alice_pkey)
        n = int(msg)
        N = math.ceil((4 + CORRECTNESS_PARAMETER)*n)
        print(N)

        for i in range(0, N):

            # Receive qubit from Alice (via Eve)
            q = Bob.recvQubit()

            # Choose a random basis
            chosen_basis = random.randint(0, 1)
            basis_list.append(chosen_basis)
            if chosen_basis == 1:
                q.H()

            # Retrieve key bit
            k = q.measure()
            raw_key.append(k)
            communication.send_message(Bob, 'Alice', skey, 'ok')

        communication.send_message(Bob, 'Alice', skey, 'DONE')

        alice_basis = communication.receive_binary_list(Bob, alice_pkey)
        communication.send_binary_list(Bob, 'Alice', skey, basis_list)
        print('ab', alice_basis)
        # print(len(alice_basis))

        diff_basis = []
        for i in range(0, len(alice_basis)):
            if alice_basis[i] != basis_list[i]:
                diff_basis.append(i)


        sifted_key = utils.remove_indices(raw_key, diff_basis)
        sifted_basis = utils.remove_indices(basis_list, diff_basis)



        # Pguess(Xr|E) = 2^((-Pwin(Tripartite game)-h(error))*num_bits, Pwin(Tripartite game)=0.23
        # min_entropy = -(-0.23 + utils.h(error_estimation)) * (len(sifted_key) - n)
        min_entropy = (len(sifted_key)-n)*(1-utils.h(error_estimation))

        if n > min_entropy - 2 * utils.log(100, 2) - 1:
            print('NOT ENOUGH MIN ENTROPY', len(sifted_key) - n, ' > ',
                  min_entropy - 2 * utils.log(100, 2) - 1)
            sys.exit(0)
        print('n={}, r={}, min_entropy={}, min_possible_entropy={}'.format(n, len(sifted_key) - n, min_entropy,
                                                                           min_entropy - 2 * utils.log(
                                                                               1.0/SECURITY_PARAMETER,
                                                                               2) - 1))

        # sifted_key = list(filter(lambda k: k != 'X', raw_key))
        # print('\n' + ''.join(sifted_key))

        # for i in range(0, len(sifted_key)):
        #     sifted_key[i] = int(sifted_key[i])

        # time.sleep(1)
        # print(type(sifted_key))

        # print('bob sending classical...')
        # Bob.sendClassical("Alice", sifted_key)
        # print('sent!')

        # seed = list(Bob.recvClassical())
        # key = 0
        # for i in range(0, len(seed)):
        #     key = (key + (int(sifted_key[i]) * seed[i])) % 2
        # print(key)



        # print('\n ========================= \n')
        # print('\n Alice basis={}'.format(alice_basis))
        """


##################################################################################################
main()
