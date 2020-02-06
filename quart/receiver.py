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
import json
import math
import os
import random
import sys

from config import Config
from scipy.linalg import toeplitz
from numpy import matmul

from cqc.pythonLib import CQCConnection, qubit
import communication
import authentication as auth
from error_correction import CascadeReceiver

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

        self.skey = auth.generate_private_key()
        self.pkey = auth.publish_public_key(self.name, self.skey)
        self.sender = ''
        self.sender_pkey = ''

        self.correctness_param = 0.0
        self.security_param = 0.0

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

            config = communication.receive_list(self.cqc, self.sender_pkey)
            self.n = config['n']
            self.correctness_param = config['correctness_param']
            self.security_param = config['security_param']
            filename = os.path.basename(config['filename'])

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
            f = open(self.name + '-' + filename, 'wb')
            f.write(plaintext)
            f.close()

    def _receive_qubits(self):
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
        # print("Performing Basis sift...", end='\r')

        receiver_basis = communication.receive_binary_list(self.cqc, self.sender_pkey)
        communication.send_binary_list(self.cqc, self.sender, self.skey, self.basis_list)

        diff_basis = []
        for i in range(0, len(receiver_basis)):
            if receiver_basis[i] != self.basis_list[i]:
                diff_basis.append(i)

        self.sifted_key = utils.remove_indices(self.raw_key, diff_basis)
        self.sifted_basis = utils.remove_indices(self.basis_list, diff_basis)
        # print("Performing Basis sift... Done!")

    def _perform_error_estimation(self):
        # print('Performing error estimation...', end='\r')

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
        # print('B Performing error estimation... Done!')
        # print('B Error rate = {}'.format(self.error_estimation))

        error_estimation_indices.sort()
        self.sifted_key = utils.remove_indices(self.sifted_key, error_estimation_indices)
        remaining_bits = len(self.sifted_key)
        min_entropy = remaining_bits * (1 - utils.h(self.error_estimation))
        max_key = min_entropy - 2 * utils.log(1/self.security_param, 2) - 1

        return self.n <= max_key

    def _perform_error_correction(self):
        if self.error_estimation == 0:
            self.error_estimation = 0.01
        CascadeReceiver(self).run_algorithm()

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


def main():
    bob = Receiver()
    bob.receive()


##################################################################################################
main()
