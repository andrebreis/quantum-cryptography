USAGE (assuming default simulaqron settings and server running):

sh run_example.sh {n}

n = int, number of qubits to be sent
Alice will send n Qubits in a randomly chosen BB84 state (using its classical value 0/1 as key)
Bob will choose a random basis for each qubit and measure it.

They will reveal their basis choices to each other and sift their keys in order to keep only the values where they used the same basis.
Then Alice generates a seed and uses the given extractor for 1 bit of key: k=Ext(x,r)=x.r mod 2 (dot = dot product)
Then Alice sends the seed to Bob who uses the seed to get the same key.

Then Alice sends the 1 bit (set to 1) message to Bob encrypted with the key and Bob can decrypt it with the key.

