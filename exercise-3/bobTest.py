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
import random
from communication import send_message, receive_message

from SimulaQron.cqc.pythonLib.cqc import CQCConnection


#####################################################################################################
#
# main
#
BASIS = ['Z', 'X']


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('n', type=int, help='Number of bits to be sent')

    return parser.parse_args().n


def main():

    n = parse_arguments()
    basis_list = []
    raw_key = []

    # Initialize the connection
    with CQCConnection("Bob") as Bob:
        Bob.closeClassicalServer()

        for i in range(0, n):

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

        alice_basis = list(receive_message(Bob))
        send_message(Bob, "Alice", bytes(basis_list))
        for i in range(0, len(alice_basis)):
            if alice_basis[i] != basis_list[i]:
                raw_key[i] = 'X'

        sifted_key = list(filter(lambda k: k != 'X', raw_key))
        print('\nBob Sifted Key:' + ''.join(sifted_key))

        seed = list(receive_message(Bob))
        key = 0
        for i in range(0, len(seed)):
            key = (key + (int(sifted_key[i]) * seed[i])) % 2
        print("Bob extracted key={}".format(key))

        c = receive_message(Bob)[0]
        m = (c + key) % 2
        print("Bob received m={} that was encrypted as c={}".format(m, c))


##################################################################################################
main()
