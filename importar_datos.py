import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Leer el CSV
df = pd.read_csv('Luna Delivery - Datos.csv', encoding='utf-8')

# Limpiar y procesar los datos
datos_limpios = []

for index, row in df.iterrows():
    # Saltar filas vacías o encabezados repetidos
    if pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == 'km':
        continue
    
    try:
        km = int(float(str(row.iloc[0]).strip().replace(',', ''))) if pd.notna(row.iloc[0]) and str(row.iloc[0]).strip() else None
        precio = float(str(row.iloc[1]).strip().replace(',', '')) if pd.notna(row.iloc[1]) and str(row.iloc[1]).strip() else None
        
        # Municipios pueden estar en diferentes columnas
        municipio = None
        for col in [2, 11]:
            if pd.notna(row.iloc[col]) and str(row.iloc[col]).strip():
                municipio = str(row.iloc[col]).strip()
                break
        
        # Colonias pueden estar en diferentes columnas
        colonia = None
        for col in [5, 12]:
            if pd.notna(row.iloc[col]) and str(row.iloc[col]).strip():
                colonia = str(row.iloc[col]).strip()
                break
        
        # CP puede estar en diferentes columnas
        cp = None
        for col in [6, 13]:
            if pd.notna(row.iloc[col]) and str(row.iloc[col]).strip():
                cp = str(row.iloc[col]).strip()
                break
        
        if municipio and colonia and cp and km and precio:
            datos_limpios.append({
                'municipio': municipio,
                'colonia': colonia,
                'cp': cp,
                'km': km,
                'precio': precio
            })
    except Exception as e:
        print(f"Error en fila {index}: {e}")
        continue

print(f"Total de registros procesados: {len(datos_limpios)}")

# Insertar en Supabase - Tabla colonias
colonias_unicas = {}
for dato in datos_limpios:
    key = f"{dato['cp']}-{dato['colonia']}"
    if key not in colonias_unicas:
        colonias_unicas[key] = {
            'municipio': dato['municipio'],
            'cp': dato['cp'],
            'colonia': dato['colonia']
        }

print(f"Insertando {len(colonias_unicas)} colonias únicas...")
for colonia_data in colonias_unicas.values():
    try:
        supabase.table('colonias').insert(colonia_data).execute()
    except Exception as e:
        print(f"Error insertando colonia {colonia_data['colonia']}: {e}")

# Insertar en Supabase - Tabla tarifas
print(f"Insertando {len(datos_limpios)} tarifas...")
for tarifa_data in datos_limpios:
    try:
        supabase.table('tarifas').insert(tarifa_data).execute()
    except Exception as e:
        print(f"Error insertando tarifa: {e}")

print("✅ ¡Importación completada!")