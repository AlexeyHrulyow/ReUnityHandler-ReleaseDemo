import hashlib

def check_password_hash():
    # Проверяем хеш пароля admin123
    password = "admin123"
    hash_result = hashlib.sha256(password.encode()).hexdigest()
    print(f"Password: {password}")
    print(f"SHA256 hash: {hash_result}")
    print(f"Hash in DB:  240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9")
    print(f"Match: {hash_result == '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9'}")

if __name__ == "__main__":
    check_password_hash()