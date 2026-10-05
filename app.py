import os
import json
import random
import math
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, send_from_directory
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='templates')

# ==========================================
# 1. CONFIGURACIÓN DE SUPABASE
# ==========================================
SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://kcwkyhfargaijkvucpeh.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtjd2t5aGZhcmdhaWprdnVjcGVoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAwODkwMjEsImV4cCI6MjEwNTY2NTAyMX0.1R2rirPSit6I-YqO2tBN2FBgSxp5Iq31fDkXVbbTCNg"

print(f" SUPABASE_URL detectada: {'✅ SÍ' if SUPABASE_URL else '❌ NO'}")
print(f"🔑 SUPABASE_KEY detectada: {'✅ SÍ' if SUPABASE_KEY else '❌ NO'}")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Conectado a Supabase exitosamente")
    except Exception as e:
        print(f"️ Error conectando a Supabase: {e}")
else:
    print("⚠️ Supabase no configurado.")

# ==========================================
# 1.5 CONFIGURACIÓN DE TARIFAS ESPECIALES
# ==========================================
MARCAS_PREMIUM = ['VS Beauty', 'VS Beauty 2', 'Ale Joyería', 'Alicia Aranda']
MARCAS_PRECIO_FIJO = {'Hane & beauty': 90}

# ==========================================
# 2. RUTAS DE VISTAS (Frontend)
# ==========================================
@app.route('/')
def home():
    return render_template('index.html', modo='cliente', token='')

@app.route('/admin')
def admin_panel():
    return render_template('index.html', modo='admin', token='')

@app.route('/repartidor')
def repartidor_panel():
    return render_template('index.html', modo='repartidor', token='')

@app.route('/rastreo/<token>')
def rastreo_publico(token):
    return render_template('index.html', modo='rastreo', token=token)

@app.route('/test-db')
def test_db():
    if not supabase:
        return jsonify({"status": "error", "message": "Supabase no configurado."}), 500
    try:
        response = supabase.table('marcas').select('id', count='exact').limit(1).execute()
        return jsonify({"status": "success", "message": f"¡Conectado! Total marcas: {response.count}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# 3. APIs DE AUTENTICACIÓN Y REGISTRO
# ==========================================
@app.route('/api/validarAccAccess', methods=['GET'])
def api_validar_acc_access():
    if not supabase: return jsonify({"result": False, "error": "Supabase no configurado"}), 500
    marca, password = request.args.get('arg0', ''), request.args.get('arg1', '')
    if not marca or not password: return jsonify({"result": False})
    try:
        response = supabase.table('marcas').select('*').ilike('nombre', marca).execute()
        if response.data and len(response.data) > 0:
            if str(response.data[0].get('password_hash', '')).strip() == str(password).strip():
                return jsonify({"result": True})
        return jsonify({"result": False})
    except Exception as e:
        return jsonify({"result": False, "error": str(e)})

@app.route('/api/registrarMarca', methods=['GET'])
def api_registrar_marca():
    if not supabase: return jsonify({"result": False}), 500
    try:
        data = json.loads(request.args.get('arg0', '{}'))
        supabase.table('marcas').insert({
            "nombre": data.get('m'), "municipio": data.get('mun'), "cp": data.get('cp'),
            "colonia": data.get('col'), "calle": data.get('calle'), "telefono": data.get('tel'),
            "password_hash": data.get('pass')
        }).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actualizarPassword', methods=['GET'])
def api_actualizar_password():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    marca, pass_actual, pass_nueva = request.args.get('arg0', ''), request.args.get('arg1', ''), request.args.get('arg2', '')
    try:
        response = supabase.table('marcas').select('*').ilike('nombre', marca).execute()
        if not response.data:
            return jsonify({"result": {"exito": False, "mensaje": "Marca no encontrada"}})
        if str(response.data[0].get('password_hash', '')).strip() != str(pass_actual).strip():
            return jsonify({"result": {"exito": False, "mensaje": "Contraseña actual incorrecta"}})
        if len(pass_nueva) < 6:
            return jsonify({"result": {"exito": False, "mensaje": "Mínimo 6 caracteres"}})
        supabase.table('marcas').update({"password_hash": pass_nueva}).eq('id', response.data[0]['id']).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Contraseña actualizada"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "mensaje": str(e)}})

@app.route('/api/recuperarPassword', methods=['GET'])
def api_recuperar_password():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    marca, telefono = request.args.get('arg0', ''), request.args.get('arg1', '')
    try:
        response = supabase.table('marcas').select('*').ilike('nombre', marca).execute()
        if response.data and str(response.data[0].get('telefono', '')).strip() == str(telefono).strip():
            return jsonify({"result": {"exito": True, "mensaje": "Tu contraseña es: " + response.data[0].get('password_hash', '')}})
        return jsonify({"result": {"exito": False, "mensaje": "Marca o teléfono no coinciden"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "mensaje": str(e)}})

# ==========================================
# 4. APIs DE PEDIDOS
# ==========================================
@app.route('/api/getPedidos', methods=['GET'])
def api_get_pedidos():
    if not supabase: return jsonify({"result": [], "error": "Supabase no configurado"}), 500
    marca = request.args.get('arg0', '')
    modo = request.args.get('arg1', 'cliente')
    status_filtro = request.args.get('arg2', '')
    
    try:
        if modo == 'admin':
            query = supabase.table('pedidos').select('*')
            
            if status_filtro == 'Entregado':
                query = query.eq('status', 'Entregado')
            elif status_filtro == 'Cancelado':
                query = query.eq('status', 'Cancelado')
            else:
                query = query.neq('status', 'Entregado').neq('status', 'Cancelado')
            
            response = query.order('creado_en', desc=True).limit(5000).execute()
            marcas_response = supabase.table('marcas').select('id, nombre').execute()
            marcas_dict = {str(m['id']): m['nombre'] for m in marcas_response.data}
        else:
            marca_response = supabase.table('marcas').select('id, nombre').ilike('nombre', marca).execute()
            if not marca_response.data: return jsonify({"result": []})
            marca_id = marca_response.data[0]['id']
            response = supabase.table('pedidos').select('*').eq('marca_id', marca_id).order('creado_en', desc=True).execute()
            marcas_dict = {str(marca_id): marca_response.data[0]['nombre']}
        
        pedidos = []
        for row in response.data:
            nombre_marca = marcas_dict.get(str(row.get('marca_id')), 'Desconocida')
            
            raw_dia = str(row.get('dia_programado', '')).strip()
            if not raw_dia or raw_dia.lower() == 'por asignar':
                dia_value = 'Por asignar'
            else:
                dia_value = raw_dia
            
            mapa_letras = {'Lunes': 'L', 'Martes': 'M', 'Miércoles': 'MI', 'Jueves': 'J', 'Viernes': 'V', 'Sábado': 'S', 'Por asignar': ''}
            dia_letra = mapa_letras.get(dia_value, '')

            pedidos.append({
                "id": row.get('id'), "token": row.get('token'), "marca": nombre_marca,
                "origen": row.get('origen', ''), "destino": row.get('destino', ''),
                "precio": float(row.get('precio', 0) or 0), "recibe": row.get('recibe_nombre', ''),
                "celular": row.get('recibe_celular', ''), "coments": row.get('comentarios', ''),
                "status": row.get('status', 'Pendiente'), "dia": dia_value,
                "diaLetra": dia_letra, "km": float(row.get('km', 0) or 0),
                "prioridad": int(row.get('prioridad', 999) or 999), "estadoPago": row.get('estado_pago', 'Pendiente'),
                "tipoServicio": row.get('tipo_servicio', 'enviar'), "direccionProveedor": row.get('direccion_proveedor', ''),
                "repartidor": row.get('repartidor_id', ''), "ordenEntrega": row.get('orden_entrega'),
                "fila": row.get('id'), "fecha": row.get('creado_en')
            })
        return jsonify({"result": pedidos})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/guardarPedido', methods=['GET'])
def api_guardar_pedido():
    if not supabase: return jsonify({"error": "Supabase no configurado"}), 500
    try:
        data = json.loads(request.args.get('arg0', '{}'))
        marca_response = supabase.table('marcas').select('id').ilike('nombre', data.get('marca', '')).execute()
        marca_id = marca_response.data[0]['id'] if marca_response.data else None
        token = data.get('marca', 'PED')[:3].upper() + str(random.randint(1000, 9999))
        
from datetime import datetime

supabase.table('pedidos').insert({
    "token": token, "marca_id": marca_id, "tipo_servicio": data.get('tipoServicio', 'enviar'),
    "origen": data.get('origen'), "destino": data.get('destino'), "precio": data.get('precio'),
    "recibe_nombre": data.get('recibe'), "recibe_celular": data.get('celular'),
    "comentarios": data.get('coments'), "km": data.get('km'), "estado_pago": "Pendiente", 
    "dia_programado": "Por asignar",
    "creado_en": datetime.now().isoformat()  # ✅ Agregar fecha actual
}).execute()
        return jsonify({"result": token})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actualizarPedido', methods=['GET'])
def api_actualizar_pedido():
    if not supabase: return jsonify({"result": False}), 500
    try:
        data = json.loads(request.args.get('arg0', '{}'))
        supabase.table('pedidos').update({
            "origen": data.get('origen'), "destino": data.get('destino'), "precio": data.get('precio'),
            "recibe_nombre": data.get('recibe'), "recibe_celular": data.get('celular'), "comentarios": data.get('coments'),
            "km": data.get('km'), "tipo_servicio": data.get('tipoServicio'), "direccion_proveedor": data.get('direccionProveedor')
        }).eq('id', int(data.get('fila'))).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cancelarPedido', methods=['GET'])
def api_cancelar_pedido():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    fila = request.args.get('arg0', '')
    try:
        supabase.table('pedidos').update({"status": "Cancelado"}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Pedido cancelado"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actualizarStatus', methods=['GET'])
def api_actualizar_status():
    if not supabase: return jsonify({"result": False}), 500
    fila, status = request.args.get('arg0', ''), request.args.get('arg1', '')
    try:
        supabase.table('pedidos').update({"status": "Entregado" if status == "Completado" else status}).eq('id', int(fila)).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actualizarDiaUnico', methods=['GET'])
def api_actualizar_dia():
    if not supabase: return jsonify({"result": False}), 500
    fila, letra = request.args.get('arg0', ''), request.args.get('arg1', '')
    mapa = {'L': 'Lunes', 'M': 'Martes', 'MI': 'Miércoles', 'J': 'Jueves', 'V': 'Viernes', 'S': 'Sábado'}
    try:
        supabase.table('pedidos').update({"dia_programado": mapa.get(letra.upper(), 'Por asignar')}).eq('id', int(fila)).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actualizarPrioridad', methods=['GET'])
def api_actualizar_prioridad():
    if not supabase: return jsonify({"result": False}), 500
    fila, valor = request.args.get('arg0', ''), request.args.get('arg1', '')
    try:
        supabase.table('pedidos').update({"prioridad": int(valor) if valor else 999}).eq('id', int(fila)).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 5. APIs DE RASTREO Y GPS
# ==========================================
@app.route('/api/obtenerDatosRastreoCliente', methods=['GET'])
def api_obtener_datos_rastreo():
    if not supabase: return jsonify({"result": {"error": "Supabase no configurado"}}), 500
    token = request.args.get('arg0', '')
    try:
        response = supabase.table('pedidos').select('status, recibe_nombre, destino, dia_programado, lat, lng, marca_id').eq('token', token).execute()
        if response.data:
            row = response.data[0]
            marca_response = supabase.table('marcas').select('nombre').eq('id', row.get('marca_id')).execute()
            return jsonify({"result": {
                "status": row.get('status'), "recibe": row.get('recibe_nombre'), 
                "marca": marca_response.data[0]['nombre'] if marca_response.data else '',
                "destino": row.get('destino'), "dia": row.get('dia_programado', 'Por asignar'),
                "mostrarMapa": row.get('status') == "En Entrega" and row.get('lat') and row.get('lng'),
                "moto": {"lat": float(row.get('lat', 0) or 0), "lng": float(row.get('lng', 0) or 0)}
            }})
        return jsonify({"result": {"error": "Pedido no encontrado"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/iniciarEntregaConGPS', methods=['GET'])
def api_iniciar_entrega_gps():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    fila, lat, lng = request.args.get('arg0', ''), request.args.get('arg1'), request.args.get('arg2')
    try:
        supabase.table('pedidos').update({
            "status": "En Entrega", "lat": float(lat) if lat else None, "lng": float(lng) if lng else None
        }).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Entrega iniciada"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/obtenerFilasEnEntrega', methods=['GET'])
def api_obtener_filas_en_entrega():
    if not supabase: return jsonify({"result": []}), 500
    try:
        response = supabase.table('pedidos').select('id').eq('status', 'En Entrega').execute()
        return jsonify({"result": [row['id'] for row in response.data]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/actualizarGPSGlobal', methods=['GET'])
def api_actualizar_gps_global():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    try:
        filas = json.loads(request.args.get('arg0', '[]'))
        lat, lng = request.args.get('arg1'), request.args.get('arg2')
        for fila in filas:
            supabase.table('pedidos').update({"lat": float(lat), "lng": float(lng)}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "cantidad": len(filas)}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 6. APIs DE REPARTIDORES
# ==========================================
@app.route('/api/getListaRepartidores', methods=['GET'])
def api_get_lista_repartidores():
    if not supabase: return jsonify({"result": []}), 500
    try:
        response = supabase.table('repartidores').select('id, nombre, telefono, activo').eq('activo', True).execute()
        return jsonify({"result": response.data})
    except Exception as e:
        return jsonify({"result": []})

@app.route('/api/asignarPedidoRepartidor', methods=['GET'])
def api_asignar_pedido_repartidor():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    fila, id_repartidor = request.args.get('arg0', ''), request.args.get('arg1', '')
    try:
        supabase.table('pedidos').update({"repartidor_id": id_repartidor if id_repartidor else None}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Pedido asignado"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/quitarAsignacionRepartidor', methods=['GET'])
def api_quitar_asignacion():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    fila = request.args.get('arg0', '')
    try:
        supabase.table('pedidos').update({"repartidor_id": None}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Asignación quitada"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# 7. APIs DE FINANZAS Y COBROS
# ==========================================
@app.route('/api/obtenerDeudaCliente', methods=['GET'])
def api_obtener_deuda():
    if not supabase: return jsonify({"result": {"pedidosPendientes": 0, "deuda": 0}}), 500
    marca = request.args.get('arg0', '')
    try:
        marca_response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
        if not marca_response.data: return jsonify({"result": {"pedidosPendientes": 0, "deuda": 0}})
        response = supabase.table('pedidos').select('precio').eq('marca_id', marca_response.data[0]['id']).eq('estado_pago', 'Pendiente').neq('status', 'Cancelado').execute()
        return jsonify({"result": {"pedidosPendientes": len(response.data), "deuda": sum(float(p.get('precio', 0) or 0) for p in response.data)}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marcarPago', methods=['GET'])
def api_marcar_pago():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    fila, estado = request.args.get('arg0', ''), request.args.get('arg1', 'Pagado')
    try:
        supabase.table('pedidos').update({"estado_pago": estado}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": f"Estado actualizado a {estado}"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/obtenerPedidosPendientes', methods=['GET'])
def api_obtener_pedidos_pendientes():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    filtro_marca = request.args.get('arg0', 'todas')
    try:
        query = supabase.table('pedidos').select('*').eq('estado_pago', 'Pendiente').neq('status', 'Cancelado')
        if filtro_marca and filtro_marca != 'todas':
            marca_response = supabase.table('marcas').select('id, nombre').ilike('nombre', filtro_marca).execute()
            if marca_response.data: query = query.eq('marca_id', marca_response.data[0]['id'])
        response = query.execute()
        marcas_response = supabase.table('marcas').select('id, nombre, telefono').execute()
        marcas_dict = {str(m['id']): {'nombre': m['nombre'], 'telefono': m.get('telefono', '')} for m in marcas_response.data}
        
        pedidos_lista = []
        for p in response.data:
            marca_info = marcas_dict.get(str(p.get('marca_id')), {'nombre': 'Desconocida', 'telefono': ''})
            pedidos_lista.append({
                'fila': p.get('id'), 'id': p.get('token', ''), 'marca': marca_info['nombre'],
                'recibe': p.get('recibe_nombre', ''), 'celular': p.get('recibe_celular', ''),
                'celularMarca': marca_info['telefono'], 'destino': p.get('destino', ''),
                'precio': float(p.get('precio', 0) or 0), 'fecha': p.get('creado_en', ''), 'status': p.get('status', 'Pendiente')
            })
        return jsonify({"result": {"exito": True, "total": len(pedidos_lista), "montoTotal": sum(p['precio'] for p in pedidos_lista), "pedidos": pedidos_lista}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/marcarPagosMasivo', methods=['GET'])
def api_marcar_pagos_masivo():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    try:
        filas = json.loads(request.args.get('arg0', '[]'))
        for fila in filas:
            supabase.table('pedidos').update({"estado_pago": "Pagado"}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": f"{len(filas)} pedido(s) marcado(s) como pagado"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/obtenerResumenSemana', methods=['GET'])
def api_obtener_resumen_semana():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    fecha_referencia_str = request.args.get('arg0', '')
    
    try:
        if fecha_referencia_str:
            fecha_ref = datetime.fromisoformat(fecha_referencia_str.replace('Z', '+00:00'))
        else:
            fecha_ref = datetime.now()
        
        ajuste = 6 if fecha_ref.weekday() == 6 else fecha_ref.weekday()
        inicio_semana = fecha_ref.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=ajuste)
        fin_semana = inicio_semana + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        inicio_str = inicio_semana.strftime('%Y-%m-%dT%H:%M:%S')
        fin_str = fin_semana.strftime('%Y-%m-%dT%H:%M:%S')
        
        print(f"📊 Semana: {inicio_str} a {fin_str}")
        
        response = supabase.table('pedidos').select('*').gte('creado_en', inicio_str).lte('creado_en', fin_str).neq('status', 'Cancelado').execute()
        pedidos = response.data
        
        print(f"📦 Pedidos encontrados en semana: {len(pedidos)}")
        
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        por_dia = {}
        for d in dias_semana:
            por_dia[d] = {"fecha": "", "pedidos": 0, "pagado": 0, "pendiente": 0, "total": 0, "pedidosLista": []}
        
        total_pedidos = 0
        total_ingresos = 0.0
        total_pagado = 0.0
        total_pendiente = 0.0
        
        for p in pedidos:
            fecha_pedido = p.get('creado_en', '')
            if not fecha_pedido:
                continue
            
            try:
                if 'T' in str(fecha_pedido):
                    f_pedido = datetime.fromisoformat(str(fecha_pedido).replace('Z', '+00:00'))
                else:
                    f_pedido = datetime.strptime(str(fecha_pedido)[:19], '%Y-%m-%d %H:%M:%S')
            except:
                continue
            
            dia_idx = f_pedido.weekday()
            dia_nombre = dias_semana[dia_idx]
            
            estado_pago = p.get('estado_pago', 'Pendiente')
            precio = float(p.get('precio', 0) or 0)
            
            total_pedidos += 1
            total_ingresos += precio
            
            if estado_pago == 'Pagado':
                total_pagado += precio
            else:
                total_pendiente += precio
            
            if not por_dia[dia_nombre]["fecha"]:
                por_dia[dia_nombre]["fecha"] = f_pedido.strftime('%d %b')
            
            por_dia[dia_nombre]["pedidos"] += 1
            por_dia[dia_nombre]["total"] += precio
            
            if estado_pago == 'Pagado':
                por_dia[dia_nombre]["pagado"] += precio
            else:
                por_dia[dia_nombre]["pendiente"] += precio
            
            por_dia[dia_nombre]["pedidosLista"].append({
                "fila": p.get('id'),
                "id": p.get('token', ''),
                "marca": p.get('marca_id', ''),
                "recibe": p.get('recibe_nombre', ''),
                "precio": precio,
                "estadoPago": estado_pago
            })
        
        rango_texto = f"{inicio_semana.strftime('%d %b')} - {fin_semana.strftime('%d %b %Y')}"
        
        return jsonify({"result": {
            "exito": True,
            "rangoTexto": rango_texto,
            "totalPedidos": total_pedidos,
            "totalIngresos": total_ingresos,
            "totalPagado": total_pagado,
            "totalPendiente": total_pendiente,
            "porDia": por_dia
        }})
    except Exception as e:
        print(f"❌ Error en resumen semana: {e}")
        return jsonify({"result": {"exito": False, "error": str(e)}}), 500

@app.route('/api/obtenerResumenRango', methods=['GET'])
def api_obtener_resumen_rango():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    fecha_inicio = request.args.get('arg0', '')
    fecha_fin = request.args.get('arg1', '')
    
    try:
        inicio_str = f"{fecha_inicio}T00:00:00"
        fin_str = f"{fecha_fin}T23:59:59"
        
        response = supabase.table('pedidos').select('*').gte('creado_en', inicio_str).lte('creado_en', fin_str).neq('status', 'Cancelado').execute()
        pedidos = response.data
        
        total_pedidos = 0
        total_ingresos = 0.0
        total_pagado = 0.0
        total_pendiente = 0.0
        pedidos_lista = []
        
        for p in pedidos:
            estado_pago = p.get('estado_pago', 'Pendiente')
            precio = float(p.get('precio', 0) or 0)
            fecha_pedido = p.get('creado_en', '')
            
            try:
                if 'T' in str(fecha_pedido):
                    f_pedido = datetime.fromisoformat(str(fecha_pedido).replace('Z', '+00:00'))
                else:
                    f_pedido = datetime.strptime(str(fecha_pedido)[:19], '%Y-%m-%d %H:%M:%S')
                fecha_formateada = f_pedido.strftime('%d/%m/%Y')
            except:
                fecha_formateada = str(fecha_pedido)[:10]
            
            total_pedidos += 1
            total_ingresos += precio
            
            if estado_pago == 'Pagado':
                total_pagado += precio
            else:
                total_pendiente += precio
            
            pedidos_lista.append({
                "fila": p.get('id'),
                "id": p.get('token', ''),
                "marca": p.get('marca_id', ''),
                "recibe": p.get('recibe_nombre', ''),
                "destino": p.get('destino', ''),
                "precio": precio,
                "estadoPago": estado_pago,
                "fecha": fecha_formateada
            })
        
        rango_texto = f"{fecha_inicio} a {fecha_fin}"
        
        return jsonify({"result": {
            "exito": True,
            "rangoTexto": rango_texto,
            "totalPedidos": total_pedidos,
            "totalIngresos": total_ingresos,
            "totalPagado": total_pagado,
            "totalPendiente": total_pendiente,
            "pedidos": pedidos_lista
        }})
    except Exception as e:
        return jsonify({"result": {"exito": False, "error": str(e)}}), 500

# ==========================================
# 8. FUNCIONES AUXILIARES PARA CÁLCULO REAL (OSRM)
# ==========================================
def obtener_coordenadas(direccion_completa):
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={direccion_completa}&countrycodes=mx&limit=1"
    headers = {'User-Agent': 'LunaDeliveryApp/1.0'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        if data and len(data) > 0:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"⚠️ Error geocodificando: {e}")
    return None, None

def calcular_distancia_por_carretera(lat_origen, lon_origen, lat_destino, lon_destino):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon_origen},{lat_origen};{lon_destino},{lat_destino}?overview=false"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('code') == 'Ok' and 'routes' in data and len(data['routes']) > 0:
            distancia_km = data['routes'][0]['distance'] / 1000.0
            print(f"️ Distancia por carretera (OSRM): {distancia_km:.2f} KM")
            return distancia_km
    except Exception as e:
        print(f"⚠️ Error con OSRM: {e}")
    
    R = 6371.0
    lat1_rad, lon1_rad = math.radians(lat_origen), math.radians(lon_origen)
    lat2_rad, lon2_rad = math.radians(lat_destino), math.radians(lon_destino)
    dlon, dlat = lon2_rad - lon1_rad, lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ==========================================
# API DE CÁLCULO DE PRECIO
# ==========================================
@app.route('/api/calcularPrecio', methods=['GET'])
def api_calcular_precio():
    if not supabase: return jsonify({"error": "Supabase no configurado", "precio": 0, "km": 0}), 500
    try:
        direccion_destino = request.args.get('arg0', '')
        marca = request.args.get('arg1', '')
        tipo_origen = request.args.get('arg2', 'marca')
        cp_destino = request.args.get('arg3', '')
        
        print(f"🔍 calcularPrecio: marca='{marca}', destino='{direccion_destino}'")
        
        if marca in MARCAS_PRECIO_FIJO:
            return jsonify({"precio": MARCAS_PRECIO_FIJO[marca], "km": 0, "origen": "Fijo", "tarifaEspecial": True})
        
        origen_completo = ""
        try:
            marca_response = supabase.table('marcas').select('calle, colonia, cp, municipio').ilike('nombre', marca).execute()
            if marca_response.data:
                m = marca_response.data[0]
                origen_completo = f"{m.get('calle', '')}, {m.get('colonia', '')}, {m.get('cp', '')}, {m.get('municipio', '')}, Jalisco, Mexico"
        except Exception as e:
            print(f"⚠️ Error obteniendo datos de marca: {e}")

        destino_completo = f"{direccion_destino}, Jalisco, Mexico"
        lat_origen, lon_origen = obtener_coordenadas(origen_completo)
        lat_destino, lon_destino = obtener_coordenadas(destino_completo)

        km_reales = 10.0
        if lat_origen and lat_destino:
            km_reales = calcular_distancia_por_carretera(lat_origen, lon_origen, lat_destino, lon_destino)
        else:
            municipio_origen = origen_completo.split(',')[-2].strip() if origen_completo else ""
            municipio_destino = direccion_destino.split(',')[-1].strip() if direccion_destino else ""
            km_reales = 5.0 if municipio_origen == municipio_destino else 15.0

        km_cobrar = math.floor(km_reales)
        tabla_tarifas = 'tarifas premiun' if marca in MARCAS_PREMIUM else 'tarifas generales'
        print(f"📊 Tabla de tarifas: '{tabla_tarifas}' | KM a cobrar: {km_cobrar}")
        
        try:
            response = supabase.table(tabla_tarifas).select('km, precio').execute()
            if not response.data:
                return jsonify({"error": f"La tabla '{tabla_tarifas}' está vacía o no existe", "precio": 0, "km": km_cobrar, "debug": "Tabla vacía"}), 500
            
            tarifas = []
            for t in response.data:
                try:
                    tarifas.append({'km': float(t.get('km', 0)), 'precio': float(t.get('precio', 0))})
                except: continue
            
            tarifas.sort(key=lambda x: x['km'])
            precio_encontrado = None
            
            for t in tarifas:
                if t['km'] <= km_cobrar:
                    precio_encontrado = t['precio']
                else:
                    break
            
            if precio_encontrado is None:
                return jsonify({"error": f"No se encontró tarifa para {km_cobrar} KM", "precio": 0, "km": km_cobrar, "debug": "KM fuera de rango"}), 500
            
            return jsonify({
                "precio": precio_encontrado, "km": km_cobrar, "km_reales": round(km_reales, 2),
                "origen": origen_completo, "destino": destino_completo, "tarifaEspecial": False,
                "tipoTarifa": tabla_tarifas, "version": "2026-10-01"
            })
        except Exception as e:
            return jsonify({"error": f"Error consultando tabla: {str(e)}", "precio": 0, "km": km_cobrar, "debug": "Error en consulta"}), 500
    except Exception as e:
        return jsonify({"error": str(e), "precio": 0, "km": 0}), 500

# ==========================================
# 9. APIs DE PERFIL Y ZONAS
# ==========================================
@app.route('/api/getMunicipios', methods=['GET'])
def api_get_municipios():
    return jsonify({"result": ['Zapopan', 'Guadalajara', 'San Pedro Tlaquepaque', 'Tlajomulco de Zúñiga', 'Tonalá']})

@app.route('/api/getCPs', methods=['GET'])
def api_get_cps():
    if not supabase: return jsonify({"result": []}), 500
    try:
        response = supabase.table('colonias').select('cp').eq('municipio', request.args.get('arg0', '')).execute()
        return jsonify({"result": sorted(list(set([row['cp'] for row in response.data if row.get('cp')])))})
    except: return jsonify({"result": []})

@app.route('/api/getColonias', methods=['GET'])
def api_get_colonias():
    if not supabase: return jsonify({"result": []}), 500
    try:
        response = supabase.table('colonias').select('colonia').eq('cp', request.args.get('arg0', '')).execute()
        return jsonify({"result": sorted(list(set([row['colonia'] for row in response.data if row.get('colonia')])))})
    except: return jsonify({"result": []})

@app.route('/api/obtenerPerfilMarca', methods=['GET'])
def api_obtener_perfil():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    try:
        response = supabase.table('marcas').select('*').ilike('nombre', request.args.get('arg0', '')).execute()
        if response.data:
            row = response.data[0]
            return jsonify({"result": {"exito": True, "marca": row.get('nombre'), "municipio": row.get('municipio'), "cp": row.get('cp'), "colonia": row.get('colonia'), "calle": row.get('calle'), "telefono": row.get('telefono'), "logo": row.get('logo_url') or "", "slogan": row.get('slogan') or ""}})
        return jsonify({"result": {"exito": False, "mensaje": "Marca no encontrada"}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/guardarPerfilMarca', methods=['GET'])
def api_guardar_perfil():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    try:
        marca = request.args.get('arg0', '')
        logo_base64 = request.args.get('arg1', '')
        mime = request.args.get('arg2', 'image/jpeg')
        slogan = request.args.get('arg3', '')
        
        response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
        if not response.data:
            return jsonify({"result": {"exito": False, "mensaje": "Marca no encontrada"}})
        
        update_data = {}
        if slogan:
            update_data["slogan"] = slogan
        
        if logo_base64:
            update_data["logo_url"] = f"data:{mime};base64,{logo_base64}"
        
        supabase.table('marcas').update(update_data).eq('id', response.data[0]['id']).execute()
        return jsonify({"result": {"exito": True, "logo": update_data.get("logo_url", ""), "mensaje": "Perfil actualizado"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "mensaje": str(e)}})

@app.route('/api/quitarLogoMarca', methods=['GET'])
def api_quitar_logo():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    try:
        marca = request.args.get('arg0', '')
        response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
        if not response.data:
            return jsonify({"result": {"exito": False, "mensaje": "Marca no encontrada"}})
        supabase.table('marcas').update({"logo_url": ""}).eq('id', response.data[0]['id']).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Logo eliminado"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "mensaje": str(e)}})

@app.route('/api/getProveedoresFrecuentes', methods=['GET'])
def api_get_proveedores():
    if not supabase: return jsonify({"result": []}), 500
    try:
        marca_response = supabase.table('marcas').select('id').ilike('nombre', request.args.get('arg0', '')).execute()
        if not marca_response.data: return jsonify({"result": []})
        response = supabase.table('proveedores').select('*').eq('marca_id', marca_response.data[0]['id']).order('nombre').execute()
        return jsonify({"result": response.data})
    except: return jsonify({"result": []})

@app.route('/api/guardarProveedorFrecuente', methods=['GET'])
def api_guardar_proveedor():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    try:
        marca = request.args.get('arg0', '')
        datos = json.loads(request.args.get('arg1', '{}'))
        marca_response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
        if not marca_response.data: return jsonify({"result": {"exito": False}})
        
        supabase.table('proveedores').insert({
            "marca_id": marca_response.data[0]['id'],
            "nombre": datos.get('nombre', ''),
            "calle": datos.get('calle', ''),
            "num_ext": datos.get('numExt', ''),
            "num_int": datos.get('numInt', ''),
            "colonia": datos.get('colonia', ''),
            "municipio": datos.get('municipio', ''),
            "cp": datos.get('cp', ''),
            "celular": datos.get('celular', '')
        }).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Proveedor guardado"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "error": str(e)}})

@app.route('/api/getDireccionTienda', methods=['GET'])
def api_get_direccion_tienda():
    if not supabase: return jsonify({"result": {"exito": False}}), 500
    try:
        response = supabase.table('marcas').select('calle, colonia, municipio, cp').ilike('nombre', request.args.get('arg0', '')).execute()
        if response.data:
            row = response.data[0]
            return jsonify({"result": {"exito": True, "direccionCompleta": f"{row.get('calle', '')}, {row.get('colonia', '')}, CP {row.get('cp', '')}, {row.get('municipio', '')}, Jalisco, Mexico"}})
        return jsonify({"result": {"exito": False}})
    except: return jsonify({"result": {"exito": False}})

@app.route('/api/getDestinatariosFrecuentes', methods=['GET'])
def api_get_destinatarios():
    if not supabase: return jsonify({"result": []}), 500
    try:
        marca_response = supabase.table('marcas').select('id').ilike('nombre', request.args.get('arg0', '')).execute()
        if not marca_response.data: return jsonify({"result": []})
        response = supabase.table('pedidos').select('recibe_nombre, recibe_celular, destino').eq('marca_id', marca_response.data[0]['id']).neq('status', 'Cancelado').execute()
        vistos, destinatarios = set(), []
        for row in response.data:
            if row.get('recibe_nombre') and row['recibe_nombre'] not in vistos:
                vistos.add(row['recibe_nombre'])
                destinatarios.append({"nombre": row['recibe_nombre'], "celular": row.get('recibe_celular'), "destino": row.get('destino')})
        return jsonify({"result": destinatarios})
    except: return jsonify({"result": []})

@app.route('/api/obtenerDatosDestinatario', methods=['GET'])
def api_obtener_datos_destinatario():
    if not supabase: return jsonify({"result": {"error": "Supabase no configurado"}}), 500
    destinatario = request.args.get('arg0', '')
    try:
        response = supabase.table('pedidos').select('destino, recibe_celular').eq('recibe_nombre', destinatario).neq('status', 'Cancelado').order('creado_en', desc=True).limit(1).execute()
        if response.data:
            destino = response.data[0].get('destino', '')
            partes = destino.split(',')
            resultado = {
                "municipio": partes[-1].strip() if len(partes) > 0 else "",
                "colonia": partes[-2].strip() if len(partes) > 1 else "",
                "cp": ""
            }
            return jsonify({"result": resultado})
        return jsonify({"result": {"error": "Destinatario no encontrado"}})
    except Exception as e:
        return jsonify({"result": {"error": str(e)}})

@app.route('/api/obtenerDireccionesOptimizadas', methods=['GET'])
def api_obtener_direcciones_optimizadas():
    if not supabase: return jsonify({"result": []}), 500
    try:
        pedidos_data = json.loads(request.args.get('arg0', '[]'))
        direcciones = []
        for p in pedidos_data:
            destino = p.get('destino', '')
            direcciones.append(f"{destino}, Jalisco, Mexico")
        return jsonify({"result": direcciones})
    except: return jsonify({"result": []})

@app.route('/api/obtenerUrlApp', methods=['GET'])
def api_obtener_url():
    return jsonify({"result": request.host_url})

@app.route('/manifest.json')
def manifest(): return send_from_directory('.', 'manifest.json', mimetype='application/json')

@app.route('/service-worker.js')
def service_worker(): return send_from_directory('.', 'service-worker.js', mimetype='application/javascript')

# ==========================================
# 10. INICIAR SERVIDOR
# ==========================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print(" LUNA DELIVERY BACKEND")
    print(f"📍 Puerto: {port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False)