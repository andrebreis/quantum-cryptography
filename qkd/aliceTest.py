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
import json
import math
from scipy.linalg import toeplitz
from numpy import matmul

from SimulaQron.cqc.pythonLib.cqc import CQCConnection, qubit
import communication
import authentication as auth
from error_correction import CascadeSender
from config import Config
from progressBar import  print_progress_bar

import argparse

import random

import utils


class Sender(object):
    def __init__(self, name="Alice"):
        self.cqc = None
        self.name = name
        self.config = Config()

        self.correctness_param = self.config.get_correctness_param()
        self.security_param = self.config.get_security_param()

        self.skey = auth.generate_private_key()
        self.pkey = auth.publish_public_key(self.name, self.skey)
        self.receiver = ''
        self.receiver_pkey = ''

        self.n = 0
        self.N = 0

        self.raw_key = []
        self.basis_list = []
        self.sifted_key = []
        self.sifted_basis = []

        self.error_estimation = 0.0

    def send(self, filename, receiver='Bob'):
        with CQCConnection(self.name) as self.cqc:
            self.cqc.closeClassicalServer()
            self.receiver = receiver
            self.receiver_pkey = auth.get_public_key(receiver)

            f = open(filename, 'rb')
            message = f.read()
            f.close()

            self.n = len(message)*8
            self.N = math.ceil((4 + self.correctness_param) * self.n) + 25
            communication.send_message(self.cqc, self.receiver, self.skey, json.dumps({
                'n': self.n,
                'security_param': self.security_param,
                'correctness_param': self.correctness_param,
                'filename': filename
            }))
            self._send_qubits()
            self._perform_basis_sift()
            can_continue = self._perform_error_estimation()
            if not can_continue:
                print('Not enough min entropy :(')
                return
            self._perform_error_correction()
            self._perform_privacy_amplification()
            cyphertext = self._encrypt(message)
            communication.send_binary_list(self.cqc, self.receiver, self.skey, cyphertext)

    def _send_qubits(self):
        print("Sending {} qubits...".format(self.N))
        for i in range(0, self.N):

            # Generate a key bit
            k = random.randint(0, 1)
            self.raw_key.append(k)
            chosen_basis = random.randint(0, 1)
            self.basis_list.append(chosen_basis)

            # Create a qubit
            q = qubit(self.cqc)

            # Encode the key in the qubit
            if k == 1:
                q.X()
            # Encode in H basis if basis = 1
            if chosen_basis == 1:
                q.H()

            self.cqc.sendQubit(q, "Eve")
            qubit_received = communication.receive_message(self.cqc, self.receiver_pkey)
            print_progress_bar(i, self.N-1)

        done_receiving = communication.receive_message(self.cqc, self.receiver_pkey)
        assert done_receiving == 'DONE'

    def _perform_basis_sift(self):
        print("Performing Basis sift...", end='\r')

        communication.send_binary_list(self.cqc, self.receiver, self.skey, self.basis_list)
        receiver_basis = communication.receive_binary_list(self.cqc, self.receiver_pkey)

        diff_basis = []
        for i in range(0, len(receiver_basis)):
            if receiver_basis[i] != self.basis_list[i]:
                diff_basis.append(i)

        self.sifted_key = utils.remove_indices(self.raw_key, diff_basis)
        self.sifted_basis = utils.remove_indices(self.basis_list, diff_basis)

        print("Performing Basis sift... Done!")

    def _perform_error_estimation(self):
        print('Performing error estimation...', end='\r')
        error_estimation_indices = []
        key_part = []
        for i in range(0, self.n):
            r = random.randint(0, len(self.sifted_key) - 1)
            while r in error_estimation_indices:
                r = random.randint(0, len(self.sifted_key) - 1)
            error_estimation_indices.append(r)
            key_part.append(self.sifted_key[r])

        communication.send_message(self.cqc, self.receiver, self.skey, error_estimation_indices)
        communication.send_binary_list(self.cqc, self.receiver, self.skey, key_part)
        receiver_key_part = communication.receive_binary_list(self.cqc, self.receiver_pkey)

        num_errors = 0.0
        for i in range(0, len(key_part)):
            if receiver_key_part[i] != key_part[i]:
                num_errors += 1.0

        self.error_estimation = num_errors / len(key_part)
        print('A Performing error estimation... Done!')
        print('A Error rate = {}'.format(self.error_estimation))

        error_estimation_indices.sort()
        self.sifted_key = utils.remove_indices(self.sifted_key, error_estimation_indices)
        remaining_bits = len(self.sifted_key)
        print(remaining_bits)
        min_entropy = remaining_bits * (1 - utils.h(self.error_estimation))
        max_key = min_entropy - 2 * utils.log(1/self.security_param, 2) - 1

        return self.n <= max_key

    def _perform_error_correction(self):
        if self.error_estimation == 0:
            self.error_estimation = 0.01
            print('Performing error correction with estimate=0.01')
        print('Performing error correction...', end='\r')
        CascadeSender(self).run_algorithm()
        print('Performing error correction... Done!')

    def _perform_privacy_amplification(self):
        seed_col, seed_row = self._generate_seed()
        communication.send_binary_list(self.cqc, self.receiver, self.skey, seed_col + seed_row)
        self.final_key = matmul(toeplitz(seed_col, seed_row), self.sifted_key)

    def _generate_seed(self):
        column = []
        for i in range(0, self.n):
            column.append(random.randint(0, 1))
        row = []
        for i in range(0, len(self.sifted_key)):
            row.append(random.randint(0, 1))
        return column, row

    def _encrypt(self, plaintext):
        bits_plaintext = communication.bytes_to_bitlist(plaintext)
        cyphertext = []
        for i in range(0, len(bits_plaintext)):
            cyphertext.append((bits_plaintext[i] + self.final_key[i]) % 2)
        return cyphertext


              #####################################################################################################
#
# main
#


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('text', type=str, help='Text to be sent')

    return parser.parse_args().text


def main():

    filename = parse_arguments()
    alice = Sender()
    alice.send(filename, "Bob")

    """
    basis_list = []
    raw_key = []

    with CQCConnection("Alice") as Alice:
        Alice.closeClassicalServer()
        # msg = auth.sign(skey, str(n))
        N = math.ceil((4 + CORRECTNESS_PARAMETER) * n)
        # Alice.sendClassical("Bob", communication.dict_to_binary(msg))
        print(N)


        for i in range(0, N):

            # Generate a key
            k = random.randint(0, 1)
            raw_key.append(k)
            chosen_basis = random.randint(0, 1)
            basis_list.append(chosen_basis)

            # Create a qubit
            q = qubit(Alice)

            # Encode the key in the qubit
            if k == 1:
                q.X()

            # Encode in H basis if basis = 1
            if chosen_basis == 1:
                q.H()

                # Send qubit to Bob (via Eve)
            # print('sending qubit {}...'.format(str(i)))
            # try:
            Alice.sendQubit(q, "Eve")
            # except Exception:
            #     time.sleep(0.25)
            #     Alice.sendQubit(q, "Eve")
            received_qubit = communication.receive_message(Alice, bob_pkey)
            print_progress_bar(i, N-1)
            # print('sent!')
    # done_receiving = communication.binary_to_dict(Alice.recvClassical())
    done_receiving = communication.receive_message(Alice, bob_pkey)
    # auth.verify(bob_pkey, done_receiving)
    print(done_receiving)
    assert done_receiving == 'DONE'

    print('BASIS SIFT')
    communication.send_binary_list(Alice, 'Bob', skey, basis_list)
    bob_basis = communication.receive_binary_list(Alice, bob_pkey)
    print(basis_list)
    print(len(bob_basis))

    diff_basis = []
    for i in range(0, len(bob_basis)):
        if bob_basis[i] != basis_list[i]:
            diff_basis.append(i)


    sifted_key = utils.remove_indices(raw_key, diff_basis)
    sifted_basis = utils.remove_indices(basis_list, diff_basis)
    print(sifted_key)

    print('ERROR ESTIMATION')
    error_estimation_indices = []
    key_part = []
    for i in range(0, n):
        r = random.randint(0, len(sifted_key)-1)
        while r in error_estimation_indices:
            r = random.randint(0, len(sifted_key)-1)
        error_estimation_indices.append(r)
        key_part.append(sifted_key[r])
        
    # print(error_estimation_indices)
    communication.send_message(Alice, 'Bob', skey, error_estimation_indices)
    communication.send_binary_list(Alice, 'Bob', skey, key_part)
    bob_key_part = communication.receive_binary_list(Alice, bob_pkey)


    num_errors = 0.0
    for i in range(0, len(key_part)):
        if bob_key_part[i] != key_part[i]:
            num_errors += 1.0

    error_estimation = num_errors/len(key_part)
    print(error_estimation)

    # Pguess(Xr|E) = 2^((-Pwin(Tripartite game)-h(error))*num_bits, Pwin(Tripartite game)=0.23
    min_entropy = -(-0.23 + utils.h(error_estimation)) * (len(sifted_key) - n)

    if len(sifted_key) - n > min_entropy - 2 * utils.log(SECURITY_PARAMETER, 2) - 1:
        # print('NOT ENOUGH MIN ENTROPY', len(sifted_key) - n, ' > ', min_entropy - 2 * utils.log(SECURITY_PARAMETER, 2) - 1)
        sys.exit(0)
    # print('n={}, r={}, min_entropy={}, min_possible_entropy={}'.format(n, len(sifted_key) - n, min_entropy,
    #                                                                    min_entropy - 2 * utils.log(SECURITY_PARAMETER,
    #                                                                                                2) - 1))
    """
    """
    # Initialize the connection
    with CQCConnection("Alice") as Alice:


        

            # Encode and send a classical message m to Bob
            # m = 1
            # enc = (m + k) % 2
            # Alice.sendClassical("Bob", enc)

        # print("\nAlice basis={}".format(basis_string))
        # print("Alice send the key k={} to Bob".format(bitstring))

        Alice.sendClassical("Bob", basis_list)
        bob_basis = Alice.recvClassical()
        bob_basis = list(bob_basis)
        # print('\n ========================= \n')
        # print(basis_list)
        # print(bob_basis)

        # print('\n' + ''.join(sifted_key))

        print("Alice waiting for classical")
        bob_key = list(Alice.recvClassical())
        print('received!')
        # print(len(sifted_key))
        # print(len(bob_key))
        print('A BAS = {}'.format(sifted_basis))
        print('A KEY = {}'.format(sifted_key))
        print('B KEY = {}'.format(bob_key))

        z_basis_error = 0.0
        x_basis_error = 0.0
        z_count = 0.0
        x_count = 0.0
        for i in range(0, len(sifted_basis)):
            if int(sifted_basis[i]) == 0:
                z_count += 1.0
                if int(sifted_key[i]) != bob_key[i]:
                    z_basis_error += 1.0
            else:
                x_count += 1.0
                if int(sifted_key[i]) != bob_key[i]:
                    x_basis_error += 1.0

        print("\n Standard Basis Error: {}\n Hadamard Basis Error: {}\n".format(z_basis_error / z_count,
                                                                                x_basis_error / x_count))

        # seed = generate_seed(len(sifted_key))
        # key = 0
        # for i in range(0, len(seed)):
        #     key = (key + (int(sifted_key[i]) * seed[i])) % 2
        # print(key)

        # Alice.sendClassical("Eve", seed)

        # Alice.sendClassical("Bob", key)

    # print(bob_basis)
    """

##################################################################################################
main()
