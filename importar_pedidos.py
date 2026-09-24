import csv
from supabase import create_client
from dotenv import load_dotenv
import os
import random
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

# Conectar a Supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

print(" Iniciando importación de pedidos...")
print("=" * 50)

# Leer el CSV
pedidos_insertados = 0
pedidos_omitidos = 0
errores = []
marcas_cache = {}

with open('Luna Delivery - Pedidos.csv', 'r', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    
    for i, row in enumerate(reader):
        try:
            # Obtener el nombre de la marca
            marca_nombre = row['Marca'].strip()
            
            # Buscar el ID de la marca (con cache)
            if marca_nombre not in marcas_cache:
                marca_response = supabase.table('marcas').select('id').ilike('nombre', marca_nombre).execute()
                if marca_response.data:
                    marcas_cache[marca_nombre] = marca_response.data[0]['id']
                else:
                    errores.append(f"Fila {i+2}: Marca '{marca_nombre}' no encontrada")
                    pedidos_omitidos += 1
                    continue
            
            marca_id = marcas_cache[marca_nombre]
            
            # Limpiar precio
            precio_str = row['Precio'].replace('$', '').replace(',', '').strip()
            try:
                precio = float(precio_str) if precio_str else 0
            except:
                precio = 0
            
            # Limpiar KM
            km_str = row['KM'].strip() if row.get('KM') else '0'
            try:
                km = float(km_str) if km_str else 0
            except:
                km = 0
            
            # Limpiar celular
            celular = row.get('Celular', '').replace(' ', '').replace('‪', '').replace('‬', '').strip()
            
            # Generar token único SIEMPRE
            id_pedido = row.get('ID Pedido', '').strip()
            if id_pedido:
                token = id_pedido
            else:
                marca_prefijo = marca_nombre[:3].upper().replace(' ', '').replace('&', '')
                token = f"{marca_prefijo}{random.randint(10000, 99999)}"
            
            # Convertir fecha
            fecha_str = row.get('Fecha', '').strip()
            fecha_iso = None
            if fecha_str:
                try:
                    fecha = datetime.strptime(fecha_str, '%m/%d/%Y %H:%M:%S')
                    fecha_iso = fecha.isoformat()
                except:
                    try:
                        fecha = datetime.strptime(fecha_str, '%d/%m/%Y %H:%M:%S')
                        fecha_iso = fecha.isoformat()
                    except:
                        fecha_iso = None
            
            # Mapear campos
            estatus = row.get('Estatus', 'Pendiente').strip()
            cobro = row.get('Cobro', 'Pendiente').strip()
            dia = row.get('Día', 'Por asignar').strip()
            tipo_servicio = row.get('envia/recibe', 'enviar').strip().lower()
            comentarios = row.get('Comentarios', '').strip()
            segunda_direccion = row.get('segunda direccion', '').strip()
            
            # Coordenadas
            lat = None
            lng = None
            try:
                if row.get('log') and row['log'].strip():
                    lat = float(row['log'].strip())
                if row.get('alt') and row['alt'].strip():
                    lng = float(row['alt'].strip())
            except:
                pass
            
            # Insertar pedido
            supabase.table('pedidos').insert({
                'token': token,
                'marca_id': marca_id,
                'tipo_servicio': tipo_servicio if tipo_servicio in ['enviar', 'recibir'] else 'enviar',
                'origen': row.get('Origen', ''),
                'destino': row.get('Destino', ''),
                'precio': precio,
                'recibe_nombre': row.get('Recibe', ''),
                'recibe_celular': celular,
                'comentarios': comentarios,
                'status': estatus,
                'estado_pago': cobro,
                'dia_programado': dia if dia else 'Por asignar',
                'km': km,
                'creado_en': fecha_iso,
                'lat': lat,
                'lng': lng,
                'direccion_proveedor': segunda_direccion if tipo_servicio == 'recibir' else None
            }).execute()
            
            pedidos_insertados += 1
            
            if pedidos_insertados % 50 == 0:
                print(f"✅ Insertados {pedidos_insertados} pedidos...")
            
        except Exception as e:
            errores.append(f"Fila {i+2}: {str(e)}")
            pedidos_omitidos += 1
            continue

print("\n" + "=" * 50)
print(f"✅ Importación completada!")
print(f"📊 Total insertados: {pedidos_insertados}")
print(f"⚠️ Total omitidos: {pedidos_omitidos}")
if errores:
    print(f"\n❌ Errores ({len(errores)}):")
    for error in errores[:20]:
        print(f"  - {error}")
print("=" * 50)