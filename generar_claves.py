from py_vapid import Vapid
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import base64

# Generar claves
vapid = Vapid()
vapid.generate_keys()

# Convertir clave pública a Base64 (formato URL-safe)
public_key_bytes = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).rstrip(b'=').decode('utf-8')

# Convertir clave privada a Base64 (formato URL-safe)
private_key_int = vapid.private_key.private_numbers().private_value
private_key_bytes = private_key_int.to_bytes(32, byteorder='big')
private_key_b64 = base64.urlsafe_b64encode(private_key_bytes).rstrip(b'=').decode('utf-8')

print("=" * 60)
print("🔑 CLAVES VAPID GENERADAS")
print("=" * 60)
print()
print("CLAVE PÚBLICA (va en el frontend):")
print(public_key_b64)
print()
print("CLAVE PRIVADA (va en el backend):")
print(private_key_b64)
print()
print("=" * 60)
print("⚠️  GUARDA ESTAS CLAVES, LAS NECESITARÁS EN LOS SIGUIENTES PASOS")
print("=" * 60)