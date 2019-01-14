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

from SimulaQron.cqc.pythonLib.cqc import CQCConnection, qubit
import argparse

import random


#####################################################################################################
#
# main
#
BASIS = ['Z', 'X']


def generate_seed(seed_len):

    seed = []
    for i in range(0, seed_len):
        seed.append(random.randint(0, 1))

    return seed


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('n', type=int, help='Number of bits to be sent')

    return parser.parse_args().n


def main():

    n = parse_arguments()
    basis_list = []
    raw_key = []

    # Initialize the connection
    with CQCConnection("Alice") as Alice:

        for i in range(0, n):

            # Generate a key
            k = random.randint(0, 1)
            raw_key.append(str(k))
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
            Alice.sendQubit(q, "Eve")

        Alice.sendClassical("Bob", basis_list)
        bob_basis = Alice.recvClassical()
        bob_basis = list(bob_basis)
        for i in range(0, len(bob_basis)):
            if bob_basis[i] != basis_list[i]:
                raw_key[i] = 'X'
                basis_list[i] = 'X'

        sifted_key = list(map(lambda k: int(k), (filter(lambda k: k != 'X', raw_key))))
        sifted_basis = list(filter(lambda k: k != 'X', basis_list))

        print("Alice waiting for classical")
        bob_key = list(Alice.recvClassical())
        Alice.sendClassical("Bob", sifted_key)
        print('received!')

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

        if z_count == 0:
            z_count = 1
        if x_count == 0:
            x_count = 1

        print("\n Standard Basis Error: {}\n Hadamard Basis Error: {}\n".format(z_basis_error / z_count,
                                                                                x_basis_error / x_count))


##################################################################################################
main()
