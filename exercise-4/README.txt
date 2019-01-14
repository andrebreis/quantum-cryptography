USAGE (assuming default simulaqron settings and server running):

sh run_example.sh {n}

n = int, number of qubits to be sent
Alice will send n Qubits in a randomly chosen BB84 state (using its classical value 0/1 as key)
Eve will intercept and measure these qubits in a random BB84 basis and send the state associated with the output she gets
Bob will choose a random basis for each qubit and measure it.

Alice and Bob will reveal their basis choices to each other and sift their keys in order to keep only the values where they used the same basis.
Then they reveal their obtained keys to each other so they can calculate the error rate for each basis


What happens? We can see that with this strategy, with many tries, the error rate approaches 25% on each basis.
So we can have some idea of the amount of information Eve is being able to extract depending on the noise caused by her.