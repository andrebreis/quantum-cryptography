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
from communication import send_message, receive_message

import random


#####################################################################################################
#
# main
#
BASIS = ['Z', 'X']


def main():

    # Initialize the connection
    with CQCConnection("Alice") as Alice:
        Alice.closeClassicalServer()

        # Generate a key
        k = random.randint(0, 1)
        chosen_basis = random.randint(0, 1)

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

        # Encode and send a classical message m to Bob
        m = 1
        enc = (m + k) % 2
        send_message(Alice, "Bob", bytes([enc]))

        print("\nAlice basis={}".format(BASIS[chosen_basis]))
        print("Alice key={}".format(k))
        print("Alice sent the message m={} to Bob".format(m))


##################################################################################################
main()
