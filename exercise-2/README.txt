USAGE (assuming default simulaqron settings and server running):

sh run_example.sh {n}

n = int, number of qubits to be sent
Alice will send n Qubits in a randomly chosen BB84 state (using its classical value 0/1 as key)
Bob will choose a random basis for each qubit and measure it.

The classical part was removed because it's not relevant for this exercise