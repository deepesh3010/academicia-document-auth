from cryptography.hazmat.primitives import hashes

def hash_file(filepath):
    digest = hashes.Hash(hashes.SHA256())
    with open(filepath, "rb") as f:
        while chunk := f.read(4096):
            digest.update(chunk)
    return digest.finalize()

if __name__ == "__main__":
    file_hash = hash_file("/Users/apple/Desktop/Project/crypto/Paper_1_Published.pdf")
    print("SHA-256 Hash:", file_hash.hex())
