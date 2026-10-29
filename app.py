import os
import json
import random
import math
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, send_from_directory
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__, static_folder='templates', static_url_path='')

# ==========================================
# 1. CONFIGURACIÓN DE SUPABASE
# ==========================================
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://kcwkyhfargaijkvucpeh.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtjd2t5aGZhcmdhaWprdnVjcGVoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTAwODkwMjEsImV4cCI6MjEwNTY2NTAyMX0.1R2rirPSit6I-YqO2tBN2FBgSxp5Iq31fDkXVbbTCNg")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

@app.route('/r/<token>')
def rastreo_corto(token):
    return render_template('index.html', modo='rastreo', token=token)

@app.route('/manifest.json')
def manifest(): 
    return send_from_directory('templates', 'manifest.json', mimetype='application/json')

@app.route('/service-worker.js')
def service_worker(): 
    return send_from_directory('templates', 'service-worker.js', mimetype='application/javascript')

# ==========================================
# 3. UTILIDAD PARA ACORTAR URLs
# ==========================================
def acortar_url(url_larga):
    try:
        response = requests.get(f"https://tinyurl.com/api-create.php?url={url_larga}", timeout=5)
        if response.status_code == 200 and response.text.startswith('http'):
            return response.text
    except:
        pass
    return url_larga

# ==========================================
# 4. APIs DE AUTENTICACIÓN Y REGISTRO
# ==========================================
@app.route('/api/validarAccAccess', methods=['GET'])
def api_validar_acc_access():
    marca = request.args.get('arg0', '').strip()
    password = request.args.get('arg1', '').strip()
    if not marca or not password:
        return jsonify({"result": False})
    
    try:
        response = supabase.table('marcas').select('*').ilike('nombre', marca).execute()
        if response.data and len(response.data) > 0:
            if str(response.data[0].get('password_hash', '')).strip() == password:
                return jsonify({"result": True})
        return jsonify({"result": False})
    except Exception as e:
        print(f"❌ Error en validarAccAccess: {e}")
        return jsonify({"result": {"error": str(e)}}), 500

@app.route('/api/registrarMarca', methods=['GET'])
def api_registrar_marca():
    try:
        data = json.loads(request.args.get('arg0', '{}'))
        supabase.table('marcas').insert({
            "nombre": data.get('m'), "municipio": data.get('mun'), "cp": data.get('cp'),
            "colonia": data.get('col'), "calle": data.get('calle'), "telefono": data.get('tel'),
            "password_hash": data.get('pass')
        }).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"result": {"error": str(e)}}), 500

@app.route('/api/actualizarPassword', methods=['GET'])
def api_actualizar_password():
    marca = request.args.get('arg0', '').strip()
    pass_actual = request.args.get('arg1', '').strip()
    pass_nueva = request.args.get('arg2', '').strip()
    
    try:
        response = supabase.table('marcas').select('*').ilike('nombre', marca).execute()
        if not response.data:
            return jsonify({"result": {"exito": False, "mensaje": "Marca no encontrada"}})
        if str(response.data[0].get('password_hash', '')).strip() != pass_actual:
            return jsonify({"result": {"exito": False, "mensaje": "Contraseña actual incorrecta"}})
        if len(pass_nueva) < 6:
            return jsonify({"result": {"exito": False, "mensaje": "Mínimo 6 caracteres"}})
        
        supabase.table('marcas').update({"password_hash": pass_nueva}).eq('id', response.data[0]['id']).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Contraseña actualizada"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "mensaje": str(e)}}), 500

@app.route('/api/recuperarPassword', methods=['GET'])
def api_recuperar_password():
    marca = request.args.get('arg0', '').strip()
    telefono = request.args.get('arg1', '').strip()
    
    try:
        response = supabase.table('marcas').select('*').ilike('nombre', marca).execute()
        if response.data and str(response.data[0].get('telefono', '')).strip() == telefono:
            return jsonify({"result": {"exito": True, "mensaje": "Tu contraseña es: " + response.data[0].get('password_hash', '')}})
        return jsonify({"result": {"exito": False, "mensaje": "Marca o teléfono no coinciden"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "mensaje": str(e)}}), 500

@app.route('/prueba-pwa')
def prueba_pwa():
    return render_template('index_pwa.html')

@app.route('/prueba-rastreo')
def prueba_rastreo():
    return render_template('rastreo_vivo.html')

# ==========================================
# 5. APIs DE PEDIDOS
# ==========================================
@app.route('/api/getPedidos', methods=['GET'])
def api_get_pedidos():
    marca = request.args.get('arg0', '').strip()
    modo = request.args.get('arg1', 'cliente')
    status_filtro = request.args.get('arg2', '')
    
    try:
        marcas_response = supabase.table('marcas').select('id, nombre').execute()
        marcas_dict = {}
        
        for m in marcas_response.data:
            marca_id = m.get('id')
            if marca_id is not None:
                marcas_dict[str(marca_id)] = m['nombre']
                try:
                    marcas_dict[int(marca_id)] = m['nombre']
                except (ValueError, TypeError):
                    pass
        
        if modo == 'admin':
            query = supabase.table('pedidos').select('*')
            if status_filtro == 'Entregado':
                query = query.eq('status', 'Entregado')
            elif status_filtro == 'Cancelado':
                query = query.eq('status', 'Cancelado')
            else:
                query = query.neq('status', 'Entregado').neq('status', 'Cancelado')
            
            response = query.order('creado_en', desc=True).limit(5000).execute()
        else:
            marca_response = supabase.table('marcas').select('id, nombre').ilike('nombre', marca).execute()
            if not marca_response.data:
                return jsonify({"result": []})
            marca_id = marca_response.data[0]['id']
            response = supabase.table('pedidos').select('*').eq('marca_id', marca_id).order('creado_en', desc=True).limit(1000).execute()
        
        pedidos = []
        for row in response.data:
            marca_id_pedido = row.get('marca_id')
            nombre_marca = 'Desconocida'
            
            if marca_id_pedido is not None:
                if str(marca_id_pedido) in marcas_dict:
                    nombre_marca = marcas_dict[str(marca_id_pedido)]
                elif marca_id_pedido in marcas_dict:
                    nombre_marca = marcas_dict[marca_id_pedido]
                elif isinstance(marca_id_pedido, str) and marca_id_pedido.lower() in {n.lower() for n in marcas_dict.values()}:
                    nombre_marca = marca_id_pedido
            
            raw_dia = str(row.get('dia_programado', '')).strip()
            dia_value = 'Por asignar' if not raw_dia or raw_dia.lower() == 'por asignar' else raw_dia
            
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
                "fila": row.get('id'), "fecha": row.get('creado_en'), "idPedido": row.get('token', '')
            })
        
        return jsonify({"result": pedidos})
    except Exception as e:
        print(f"❌ Error en getPedidos: {e}")
        return jsonify({"result": {"error": str(e)}}), 500

@app.route('/api/guardarPedido', methods=['GET'])
def api_guardar_pedido():
    try:
        data = json.loads(request.args.get('arg0', '{}'))
        marca_response = supabase.table('marcas').select('id').ilike('nombre', data.get('marca', '')).execute()
        marca_id = marca_response.data[0]['id'] if marca_response.data else None
        
        prefijo = data.get('marca', 'PED')[:3].upper()
        token = prefijo + str(random.randint(1000, 9999))
        
        supabase.table('pedidos').insert({
            "token": token, "marca_id": marca_id, "tipo_servicio": data.get('tipoServicio', 'enviar'),
            "origen": data.get('origen'), "destino": data.get('destino'), "precio": data.get('precio'),
            "recibe_nombre": data.get('recibe'), "recibe_celular": data.get('celular'),
            "comentarios": data.get('coments'), "km": data.get('km'), "estado_pago": "Pendiente", 
            "dia_programado": "Por asignar", "prioridad": 999,
            "creado_en": datetime.now().isoformat()
        }).execute()
        return jsonify({"result": token})
    except Exception as e:
        return jsonify({"result": {"error": str(e)}}), 500

@app.route('/api/actualizarPedido', methods=['GET'])
def api_actualizar_pedido():
    try:
        data = json.loads(request.args.get('arg0', '{}'))
        supabase.table('pedidos').update({
            "origen": data.get('origen'), "destino": data.get('destino'), "precio": data.get('precio'),
            "recibe_nombre": data.get('recibe'), "recibe_celular": data.get('celular'), "comentarios": data.get('coments'),
            "km": data.get('km'), "tipo_servicio": data.get('tipoServicio'), "direccion_proveedor": data.get('direccionProveedor')
        }).eq('id', int(data.get('fila'))).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"result": {"error": str(e)}}), 500

@app.route('/api/cancelarPedido', methods=['GET'])
def api_cancelar_pedido():
    fila = request.args.get('arg0', '')
    marca = request.args.get('arg1', '')
    try:
        pedido = supabase.table('pedidos').select('status, marca_id').eq('id', int(fila)).execute()
        if not pedido.data:
            return jsonify({"result": {"exito": False, "mensaje": "Pedido no encontrado"}})
        if pedido.data[0]['status'] in ['En Entrega', 'Entregado']:
            return jsonify({"result": {"exito": False, "mensaje": "No se puede cancelar un pedido en entrega o entregado"}})
            
        supabase.table('pedidos').update({"status": "Cancelado"}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Pedido cancelado correctamente"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "mensaje": str(e)}}), 500

@app.route('/api/actualizarStatus', methods=['GET'])
def api_actualizar_status():
    fila = request.args.get('arg0', '')
    status = request.args.get('arg1', '')
    try:
        nuevo_status = "Entregado" if status == "Completado" else status
        supabase.table('pedidos').update({"status": nuevo_status}).eq('id', int(fila)).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"result": {"error": str(e)}}), 500

@app.route('/api/actualizarDiaUnico', methods=['GET'])
def api_actualizar_dia():
    fila = request.args.get('arg0', '')
    letra = request.args.get('arg1', '')
    mapa = {'L': 'Lunes', 'M': 'Martes', 'MI': 'Miércoles', 'J': 'Jueves', 'V': 'Viernes', 'S': 'Sábado'}
    try:
        supabase.table('pedidos').update({"dia_programado": mapa.get(letra.upper(), 'Por asignar')}).eq('id', int(fila)).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"result": {"error": str(e)}}), 500

@app.route('/api/actualizarPrioridad', methods=['GET'])
def api_actualizar_prioridad():
    fila = request.args.get('arg0', '')
    valor = request.args.get('arg1', '')
    try:
        supabase.table('pedidos').update({"prioridad": int(valor) if valor else 999}).eq('id', int(fila)).execute()
        return jsonify({"result": True})
    except Exception as e:
        return jsonify({"result": {"error": str(e)}}), 500

# ==========================================
# 6. APIs DE RASTREO Y GPS
# ==========================================
@app.route('/api/obtenerDatosRastreoCliente', methods=['GET'])
def api_obtener_datos_rastreo():
    token = request.args.get('arg0', '')
    try:
        response = supabase.table('pedidos').select('status, recibe_nombre, destino, dia_programado, lat, lng, marca_id, tipo_servicio, direccion_proveedor').eq('token', token).execute()
        if response.data:
            row = response.data[0]
            marca_response = supabase.table('marcas').select('nombre').eq('id', row.get('marca_id')).execute()
            marca_nombre = marca_response.data[0]['nombre'] if marca_response.data else ''
            
            return jsonify({"result": {
                "status": row.get('status'), "recibe": row.get('recibe_nombre'), 
                "marca": marca_nombre, "destino": row.get('destino'), 
                "dia": row.get('dia_programado', 'Por asignar'),
                "mostrarMapa": row.get('status') == "En Entrega" and row.get('lat') and row.get('lng'),
                "moto": {"lat": float(row.get('lat', 0) or 0), "lng": float(row.get('lng', 0) or 0)},
                "tipoServicio": row.get('tipo_servicio', 'enviar'),
                "direccionProveedor": row.get('direccion_proveedor', '')
            }})
        return jsonify({"result": {"error": "Pedido no encontrado"}})
    except Exception as e:
        return jsonify({"result": {"error": str(e)}}), 500

@app.route('/api/iniciarEntregaConGPS', methods=['GET'])
def api_iniciar_entrega_gps():
    fila = request.args.get('arg0', '')
    lat = request.args.get('arg1')
    lng = request.args.get('arg2')
    try:
        supabase.table('pedidos').update({
            "status": "En Entrega", 
            "lat": float(lat) if lat else None, 
            "lng": float(lng) if lng else None
        }).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Entrega iniciada"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "error": str(e)}}), 500

@app.route('/api/obtenerFilasEnEntrega', methods=['GET'])
def api_obtener_filas_en_entrega():
    try:
        response = supabase.table('pedidos').select('id').eq('status', 'En Entrega').execute()
        return jsonify({"result": [row['id'] for row in response.data]})
    except Exception as e:
        return jsonify({"result": {"error": str(e)}}), 500

@app.route('/api/actualizarGPSGlobal', methods=['GET'])
def api_actualizar_gps_global():
    try:
        filas = json.loads(request.args.get('arg0', '[]'))
        lat = request.args.get('arg1')
        lng = request.args.get('arg2')
        for fila in filas:
            supabase.table('pedidos').update({"lat": float(lat), "lng": float(lng)}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "cantidad": len(filas)}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "error": str(e)}}), 500

# ==========================================
# 7. APIs DE REPARTIDORES
# ==========================================
@app.route('/api/getListaRepartidores', methods=['GET'])
def api_get_lista_repartidores():
    try:
        response = supabase.table('repartidores').select('id, nombre, telefono, activo').eq('activo', True).execute()
        return jsonify({"result": response.data})
    except Exception:
        return jsonify({"result": []})

@app.route('/api/asignarPedidoRepartidor', methods=['GET'])
def api_asignar_pedido_repartidor():
    fila = request.args.get('arg0', '')
    id_repartidor = request.args.get('arg1', '')
    try:
        supabase.table('pedidos').update({"repartidor_id": id_repartidor if id_repartidor else None}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Pedido asignado correctamente"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "mensaje": str(e)}}), 500

@app.route('/api/quitarAsignacionRepartidor', methods=['GET'])
def api_quitar_asignacion():
    fila = request.args.get('arg0', '')
    try:
        supabase.table('pedidos').update({"repartidor_id": None}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Asignación quitada correctamente"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "mensaje": str(e)}}), 500

# ==========================================
# 8. APIs DE FINANZAS Y COBROS (CON MANEJO SEGURO DE ERRORES)
# ==========================================
@app.route('/api/obtenerDeudaCliente', methods=['GET'])
def api_obtener_deuda():
    """
    Calcula la deuda de una marca.
    IMPORTANTE: Si hay error, devuelve error dentro de result para que el frontend lo detecte.
    """
    marca = request.args.get('arg0', '').strip()
    print(f"🔍 [BACKEND] Buscando deuda para: '{marca}'")
    
    try:
        # 1. Obtener ID de la marca
        marca_response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
        if not marca_response.data:
            print(f"️ [BACKEND] Marca '{marca}' no encontrada")
            return jsonify({"result": {"pedidosPendientes": 0, "deuda": 0, "diasMasAntiguo": 0}})
        
        marca_id = marca_response.data[0]['id']
        print(f"✅ [BACKEND] ID de marca encontrado: {marca_id}")
        
        # 2. Obtener pedidos
        response = supabase.table('pedidos').select('precio, creado_en, estado_pago, status').eq('marca_id', marca_id).execute()
        print(f"📦 [BACKEND] Total pedidos en BD: {len(response.data)}")
        
        deuda = 0.0
        pedidos_pendientes = 0
        fecha_mas_antigua = None
        hoy = datetime.now()
        
        # 3. Filtrar manualmente (case-insensitive)
        for p in response.data:
            estado_pago = str(p.get('estado_pago', 'Pendiente')).strip().lower()
            status = str(p.get('status', '')).strip()
            
            if estado_pago == "pendiente" and status != "Cancelado":
                deuda += float(p.get('precio', 0) or 0)
                pedidos_pendientes += 1
                
                if p.get('creado_en'):
                    try:
                        fecha_str = str(p['creado_en'])
                        if 'Z' in fecha_str:
                            fecha_str = fecha_str.replace('Z', '+00:00')
                        fecha_pedido = datetime.fromisoformat(fecha_str)
                        if fecha_pedido.tzinfo is not None:
                            fecha_pedido = fecha_pedido.replace(tzinfo=None)
                        if fecha_mas_antigua is None or fecha_pedido < fecha_mas_antigua:
                            fecha_mas_antigua = fecha_pedido
                    except Exception as e:
                        print(f"⚠️ Error parseando fecha {p['creado_en']}: {e}")
        
        # 4. Calcular días
        dias_mas_antiguo = 0
        if fecha_mas_antigua:
            diff_tiempo = hoy - fecha_mas_antigua
            dias_mas_antiguo = int(diff_tiempo.total_seconds() // 86400)
        
        print(f"✅ [BACKEND] RESULTADO -> Pedidos: {pedidos_pendientes}, Deuda: ${deuda}, Días: {dias_mas_antiguo}")
        
        # ✅ RETORNO SEGURO: siempre dentro de "result"
        return jsonify({"result": {
            "pedidosPendientes": pedidos_pendientes,
            "deuda": deuda,
            "diasMasAntiguo": dias_mas_antiguo
        }})
        
    except Exception as e:
        print(f" [BACKEND] ERROR en obtenerDeudaCliente: {e}")
        import traceback
        traceback.print_exc()
        # ⚠️ IMPORTANTE: Devolver error dentro de result para que gs() lo detecte
        return jsonify({"result": {"error": str(e), "pedidosPendientes": 0, "deuda": 0, "diasMasAntiguo": 0}}), 500

@app.route('/api/marcarPago', methods=['GET'])
def api_marcar_pago():
    fila = request.args.get('arg0', '')
    estado = request.args.get('arg1', 'Pagado')
    try:
        supabase.table('pedidos').update({"estado_pago": estado}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": f"Estado actualizado a {estado}"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "error": str(e)}}), 500

@app.route('/api/obtenerPedidosPendientes', methods=['GET'])
def api_obtener_pedidos_pendientes():
    filtro_marca = request.args.get('arg0', 'todas').strip()
    try:
        query = supabase.table('pedidos').select('*').eq('estado_pago', 'Pendiente').neq('status', 'Cancelado')
        if filtro_marca and filtro_marca != 'todas':
            marca_response = supabase.table('marcas').select('id, nombre').ilike('nombre', filtro_marca).execute()
            if marca_response.data:
                query = query.eq('marca_id', marca_response.data[0]['id'])
                
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
                'precio': float(p.get('precio', 0) or 0), 'fecha': p.get('creado_en', '')[:10] if p.get('creado_en') else '',
                'status': p.get('status', 'Pendiente')
            })
            
        pedidos_lista.sort(key=lambda x: x['fila'], reverse=True)
        monto_total = sum(p['precio'] for p in pedidos_lista)
        
        return jsonify({"result": {"exito": True, "total": len(pedidos_lista), "montoTotal": monto_total, "pedidos": pedidos_lista}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "error": str(e)}}), 500

@app.route('/api/marcarPagosMasivo', methods=['GET'])
def api_marcar_pagos_masivo():
    try:
        filas = json.loads(request.args.get('arg0', '[]'))
        for fila in filas:
            supabase.table('pedidos').update({"estado_pago": "Pagado"}).eq('id', int(fila)).execute()
        return jsonify({"result": {"exito": True, "mensaje": f"{len(filas)} pedido(s) marcado(s) como pagado"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "error": str(e)}}), 500

@app.route('/api/obtenerResumenSemana', methods=['GET'])
def api_obtener_resumen_semana():
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
        
        response = supabase.table('pedidos').select('*').gte('creado_en', inicio_str).lte('creado_en', fin_str).neq('status', 'Cancelado').execute()
        pedidos = response.data
        
        dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        por_dia = {d: {"fecha": "", "pedidos": 0, "pagado": 0, "pendiente": 0, "total": 0, "pedidosLista": []} for d in dias_semana}
        
        total_pedidos = 0
        total_ingresos = 0.0
        total_pagado = 0.0
        total_pendiente = 0.0
        
        for p in pedidos:
            fecha_pedido = p.get('creado_en', '')
            if not fecha_pedido: continue
            try:
                f_pedido = datetime.fromisoformat(str(fecha_pedido).replace('Z', '+00:00'))
            except: continue
            
            dia_idx = f_pedido.weekday()
            dia_nombre = dias_semana[dia_idx]
            estado_pago = p.get('estado_pago', 'Pendiente')
            precio = float(p.get('precio', 0) or 0)
            
            total_pedidos += 1
            total_ingresos += precio
            if estado_pago == 'Pagado': total_pagado += precio
            else: total_pendiente += precio
            
            if not por_dia[dia_nombre]["fecha"]:
                por_dia[dia_nombre]["fecha"] = f_pedido.strftime('%d %b')
            
            por_dia[dia_nombre]["pedidos"] += 1
            por_dia[dia_nombre]["total"] += precio
            if estado_pago == 'Pagado': por_dia[dia_nombre]["pagado"] += precio
            else: por_dia[dia_nombre]["pendiente"] += precio
            
            por_dia[dia_nombre]["pedidosLista"].append({
                "fila": p.get('id'), "id": p.get('token', ''), "marca": p.get('marca_id', ''),
                "recibe": p.get('recibe_nombre', ''), "precio": precio, "estadoPago": estado_pago
            })
        
        rango_texto = f"{inicio_semana.strftime('%d %b')} - {fin_semana.strftime('%d %b %Y')}"
        return jsonify({"result": {
            "exito": True, "rangoTexto": rango_texto, "totalPedidos": total_pedidos,
            "totalIngresos": total_ingresos, "totalPagado": total_pagado,
            "totalPendiente": total_pendiente, "porDia": por_dia
        }})
    except Exception as e:
        return jsonify({"result": {"exito": False, "error": str(e)}}), 500

@app.route('/api/obtenerResumenRango', methods=['GET'])
def api_obtener_resumen_rango():
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
                f_pedido = datetime.fromisoformat(str(fecha_pedido).replace('Z', '+00:00'))
                fecha_formateada = f_pedido.strftime('%d/%m/%Y')
            except:
                fecha_formateada = str(fecha_pedido)[:10] if fecha_pedido else ''
            
            total_pedidos += 1
            total_ingresos += precio
            if estado_pago == 'Pagado': total_pagado += precio
            else: total_pendiente += precio
            
            pedidos_lista.append({
                "fila": p.get('id'), "id": p.get('token', ''), "marca": p.get('marca_id', ''),
                "recibe": p.get('recibe_nombre', ''), "destino": p.get('destino', ''),
                "precio": precio, "estadoPago": estado_pago, "fecha": fecha_formateada
            })
        
        rango_texto = f"{fecha_inicio} a {fecha_fin}"
        return jsonify({"result": {
            "exito": True, "rangoTexto": rango_texto, "totalPedidos": total_pedidos,
            "totalIngresos": total_ingresos, "totalPagado": total_pagado,
            "totalPendiente": total_pendiente, "pedidos": pedidos_lista
        }})
    except Exception as e:
        return jsonify({"result": {"exito": False, "error": str(e)}}), 500

# ==========================================
# 9. CÁLCULO DE PRECIO (OSRM)
# ==========================================
def obtener_coordenadas(direccion_completa):
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={direccion_completa}&countrycodes=mx&limit=1"
    headers = {'User-Agent': 'LunaDeliveryApp/1.0'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        if data and len(data) > 0:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        pass
    return None, None

def calcular_distancia_por_carretera(lat_origen, lon_origen, lat_destino, lon_destino):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon_origen},{lat_origen};{lon_destino},{lat_destino}?overview=false"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('code') == 'Ok' and 'routes' in data and len(data['routes']) > 0:
            return data['routes'][0]['distance'] / 1000.0
    except Exception:
        pass
    R = 6371.0
    lat1_rad, lon1_rad = math.radians(lat_origen), math.radians(lon_origen)
    lat2_rad, lon2_rad = math.radians(lat_destino), math.radians(lon_destino)
    dlon, dlat = lon2_rad - lon1_rad, lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

@app.route('/api/calcularPrecio', methods=['GET'])
def api_calcular_precio():
    try:
        destino_input = request.args.get('arg0', '').strip()
        marca = request.args.get('arg1', '').strip()
        tipo_origen = request.args.get('arg2', 'marca')
        cp_destino = request.args.get('arg3', '')
        
        print(f" CALCULAR PRECIO - Marca: '{marca}', Tipo: '{tipo_origen}', Destino: '{destino_input}'")
        
        marca_norm = marca.lower().replace('&', 'and').replace(' ', '')
        
        if 'hane' in marca_norm and 'beauty' in marca_norm:
            return jsonify({"result": {"precio": 90, "km": 0, "origen": "Fijo", "tarifaEspecial": True}})
            
        origen_completo = ""
        destino_completo = ""
        
        if tipo_origen == "recibir":
            origen_completo = destino_input + ", Jalisco, Mexico"
            marca_response = supabase.table('marcas').select('calle, colonia, cp, municipio').ilike('nombre', marca).execute()
            if marca_response.data:
                m = marca_response.data[0]
                destino_completo = f"{m.get('calle', '')}, {m.get('colonia', '')}, {m.get('cp', '')}, {m.get('municipio', '')}, Jalisco, Mexico"
            else:
                return jsonify({"result": {"precio": "Marca no registrada", "km": 0}})
        elif tipo_origen == "hub":
            origen_completo = "Manuel M. Dieguez 236, Jocotan, Zapopan, Jalisco, Mexico"
            destino_completo = destino_input + ", Jalisco, Mexico"
            if cp_destino in ['45000', '45010', '45020']:
                return jsonify({"result": {"precio": 75, "km": "N/A (Fijo)", "origen": origen_completo}})
        else:
            marca_response = supabase.table('marcas').select('calle, colonia, cp, municipio').ilike('nombre', marca).execute()
            if marca_response.data:
                m = marca_response.data[0]
                origen_completo = f"{m.get('calle', '')}, {m.get('colonia', '')}, {m.get('cp', '')}, {m.get('municipio', '')}, Jalisco, Mexico"
            else:
                return jsonify({"result": {"precio": "Marca no registrada", "km": 0}})
            destino_completo = destino_input + ", Jalisco, Mexico"

        lat_origen, lon_origen = obtener_coordenadas(origen_completo)
        lat_destino, lon_destino = obtener_coordenadas(destino_completo)
        
        km_reales = 10.0
        if lat_origen and lat_destino:
            km_reales = calcular_distancia_por_carretera(lat_origen, lon_origen, lat_destino, lon_destino)
        else:
            km_reales = 15.0
            
        km_cobrar = math.floor(km_reales)
        print(f"📏 KM Reales: {km_reales}, KM Cobrar: {km_cobrar}")
        
        es_premium = any(p in marca_norm for p in ['vsbeauty', 'aleayala', 'alejoyeria'])
        tabla_tarifas = 'tarifas_premiun' if es_premium else 'tarifas_generales'
        print(f"💰 Tabla a usar: {tabla_tarifas}")
        
        try:
            response = supabase.table(tabla_tarifas).select('km, precio').execute()
            print(f"📋 Registros encontrados: {len(response.data)}")
            
            if not response.data:
                print(f"⚠️ Tabla {tabla_tarifas} está vacía")
                return jsonify({"result": {"precio": 0, "km": km_cobrar, "debug": "Tabla vacía", "tabla": tabla_tarifas}})
            
            # Mostrar primeros 3 registros para debug
            print(f"🔎 Primeros registros: {response.data[:3]}")
            
            tarifas = []
            for t in response.data:
                try:
                    # Conversión robusta: limpiar espacios y convertir
                    km_str = str(t.get('km', '0')).strip()
                    precio_str = str(t.get('precio', '0')).strip()
                    
                    km_val = float(km_str) if km_str else 0.0
                    precio_val = float(precio_str) if precio_str else 0.0
                    
                    tarifas.append({'km': km_val, 'precio': precio_val})
                except Exception as e:
                    print(f"️ Error convirtiendo registro: {t} - {e}")
            
            tarifas.sort(key=lambda x: x['km'])
            print(f"✅ Tarifas ordenadas: {len(tarifas)} registros válidos")
            
            precio_encontrado = None
            for t in tarifas:
                if t['km'] <= km_cobrar:
                    precio_encontrado = t['precio']
                    print(f"   ✓ {t['km']} km <= {km_cobrar} → Precio: ${t['precio']}")
                else:
                    print(f"   ✗ {t['km']} km > {km_cobrar} → Break")
                    break
                    
            if precio_encontrado is None:
                precio_encontrado = tarifas[-1]['precio'] if tarifas else 0
                print(f"️ No se encontró tramo exacto, usando último: ${precio_encontrado}")
            
            print(f"💵 PRECIO FINAL: ${precio_encontrado}")
                
            return jsonify({"result": {
                "precio": precio_encontrado, 
                "km": km_cobrar, 
                "km_reales": round(km_reales, 2),
                "origen": origen_completo, 
                "destino": destino_completo, 
                "tarifaEspecial": False,
                "tipoTarifa": tabla_tarifas
            }})
        except Exception as e:
            print(f"❌ Error en consulta de tarifas: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"result": {"precio": 0, "km": km_cobrar, "debug": str(e)}})
    except Exception as e:
        print(f"❌ Error general: {e}")
        return jsonify({"result": {"error": str(e), "precio": 0, "km": 0}}), 500
# ==========================================
# 10. APIs DE PERFIL Y ZONAS
# ==========================================
@app.route('/api/getMunicipios', methods=['GET'])
def api_get_municipios():
    return jsonify({"result": ['Zapopan', 'Guadalajara', 'San Pedro Tlaquepaque', 'Tlajomulco de Zúñiga', 'Tonalá']})

@app.route('/api/getCPs', methods=['GET'])
def api_get_cps():
    m = request.args.get('arg0', '')
    try:
        response = supabase.table('colonias').select('cp').eq('municipio', m).execute()
        cps = sorted(list(set([row['cp'] for row in response.data if row.get('cp')])))
        return jsonify({"result": cps})
    except Exception:
        return jsonify({"result": []})

@app.route('/api/getColonias', methods=['GET'])
def api_get_colonias():
    cp = request.args.get('arg0', '')
    try:
        response = supabase.table('colonias').select('colonia').eq('cp', cp).execute()
        colonias = sorted(list(set([row['colonia'] for row in response.data if row.get('colonia')])))
        return jsonify({"result": colonias})
    except Exception:
        return jsonify({"result": []})

@app.route('/api/obtenerPerfilMarca', methods=['GET'])
def api_obtener_perfil():
    marca = request.args.get('arg0', '').strip()
    try:
        response = supabase.table('marcas').select('*').ilike('nombre', marca).execute()
        if response.data:
            row = response.data[0]
            return jsonify({"result": {
                "exito": True, "marca": row.get('nombre'), "municipio": row.get('municipio'), 
                "cp": row.get('cp'), "colonia": row.get('colonia'), "calle": row.get('calle'), 
                "telefono": row.get('telefono'), "logo": row.get('logo_url') or "", 
                "slogan": row.get('slogan') or ""
            }})
        return jsonify({"result": {"exito": False, "mensaje": "Marca no encontrada"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "mensaje": str(e)}}), 500

@app.route('/api/guardarPerfilMarca', methods=['GET'])
def api_guardar_perfil():
    try:
        marca = request.args.get('arg0', '').strip()
        logo_base64 = request.args.get('arg1', '')
        mime = request.args.get('arg2', 'image/jpeg')
        slogan = request.args.get('arg3', '')
        
        response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
        if not response.data:
            return jsonify({"result": {"exito": False, "mensaje": "Marca no encontrada"}})
        
        update_data = {}
        if slogan: update_data["slogan"] = slogan
        if logo_base64: 
            update_data["logo_url"] = f"data:{mime};base64,{logo_base64}"
        
        supabase.table('marcas').update(update_data).eq('id', response.data[0]['id']).execute()
        return jsonify({"result": {"exito": True, "logo": update_data.get("logo_url", ""), "mensaje": "Perfil actualizado correctamente"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "mensaje": str(e)}}), 500

@app.route('/api/quitarLogoMarca', methods=['GET'])
def api_quitar_logo():
    try:
        marca = request.args.get('arg0', '').strip()
        response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
        if not response.data:
            return jsonify({"result": {"exito": False, "mensaje": "Marca no encontrada"}})
        supabase.table('marcas').update({"logo_url": ""}).eq('id', response.data[0]['id']).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Foto eliminada"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "mensaje": str(e)}}), 500

@app.route('/api/getProveedoresFrecuentes', methods=['GET'])
def api_get_proveedores():
    marca = request.args.get('arg0', '').strip()
    try:
        marca_response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
        if not marca_response.data: return jsonify({"result": []})
        
        response = supabase.table('proveedores').select('*').eq('marca_id', marca_response.data[0]['id']).order('nombre').execute()
        proveedores = [{
            "nombre": r.get('nombre', ''), "calle": r.get('calle', ''), "numExt": r.get('num_ext', ''),
            "numInt": r.get('num_int', ''), "colonia": r.get('colonia', ''), "municipio": r.get('municipio', ''),
            "cp": r.get('cp', ''), "celular": r.get('celular', '')
        } for r in response.data]
        return jsonify({"result": proveedores})
    except Exception:
        return jsonify({"result": []})

@app.route('/api/guardarProveedorFrecuente', methods=['GET'])
def api_guardar_proveedor():
    try:
        marca = request.args.get('arg0', '').strip()
        datos = json.loads(request.args.get('arg1', '{}'))
        
        marca_response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
        if not marca_response.data: return jsonify({"result": {"exito": False}})
        
        existentes = supabase.table('proveedores').select('*').eq('marca_id', marca_response.data[0]['id']).execute()
        for ex in existentes.data:
            if ex.get('nombre') == datos.get('nombre') and ex.get('calle') == datos.get('calle'):
                return jsonify({"result": {"exito": True, "mensaje": "Ya existe este proveedor", "duplicado": True}})
        
        supabase.table('proveedores').insert({
            "marca_id": marca_response.data[0]['id'], "nombre": datos.get('nombre', ''),
            "calle": datos.get('calle', ''), "num_ext": datos.get('numExt', ''),
            "num_int": datos.get('numInt', ''), "colonia": datos.get('colonia', ''),
            "municipio": datos.get('municipio', ''), "cp": datos.get('cp', ''), "celular": datos.get('celular', '')
        }).execute()
        return jsonify({"result": {"exito": True, "mensaje": "Proveedor guardado correctamente"}})
    except Exception as e:
        return jsonify({"result": {"exito": False, "error": str(e)}}), 500

@app.route('/api/getDireccionTienda', methods=['GET'])
def api_get_direccion_tienda():
    marca = request.args.get('arg0', '').strip()
    try:
        response = supabase.table('marcas').select('calle, colonia, municipio, cp').ilike('nombre', marca).execute()
        if response.data:
            row = response.data[0]
            return jsonify({"result": {
                "exito": True, 
                "direccionCompleta": f"{row.get('calle', '')}, {row.get('colonia', '')}, CP {row.get('cp', '')}, {row.get('municipio', '')}, Jalisco, Mexico"
            }})
        return jsonify({"result": {"exito": False}})
    except Exception:
        return jsonify({"result": {"exito": False}})

@app.route('/api/getDestinatariosFrecuentes', methods=['GET'])
def api_get_destinatarios():
    marca = request.args.get('arg0', '').strip()
    try:
        marca_response = supabase.table('marcas').select('id').ilike('nombre', marca).execute()
        if not marca_response.data: return jsonify({"result": []})
        
        response = supabase.table('pedidos').select('recibe_nombre, recibe_celular, destino').eq('marca_id', marca_response.data[0]['id']).neq('status', 'Cancelado').order('creado_en', desc=True).execute()
        
        vistos, destinatarios = set(), []
        for row in response.data:
            nombre = row.get('recibe_nombre')
            if nombre and nombre not in vistos:
                vistos.add(nombre)
                destinatarios.append({"nombre": nombre, "celular": row.get('recibe_celular'), "destino": row.get('destino')})
        return jsonify({"result": destinatarios})
    except Exception:
        return jsonify({"result": []})

@app.route('/api/obtenerDatosDestinatario', methods=['GET'])
def api_obtener_datos_destinatario():
    destinatario = request.args.get('arg0', '').strip()
    try:
        response = supabase.table('pedidos').select('destino, recibe_celular').eq('recibe_nombre', destinatario).neq('status', 'Cancelado').order('creado_en', desc=True).limit(1).execute()
        if response.data:
            destino = response.data[0].get('destino', '')
            partes = destino.split(',')
            return jsonify({"result": {
                "municipio": partes[-1].strip() if len(partes) > 0 else "",
                "colonia": partes[-2].strip() if len(partes) > 1 else "", "cp": ""
            }})
        return jsonify({"result": {"error": "Destinatario no encontrado"}})
    except Exception as e:
        return jsonify({"result": {"error": str(e)}}), 500

@app.route('/api/obtenerDireccionesOptimizadas', methods=['GET'])
def api_obtener_direcciones_optimizadas():
    try:
        pedidos_data = json.loads(request.args.get('arg0', '[]'))
        direcciones = [f"{p.get('destino', '')}, Jalisco, Mexico" for p in pedidos_data]
        return jsonify({"result": direcciones})
    except Exception:
        return jsonify({"result": []})

@app.route('/api/obtenerUrlApp', methods=['GET'])
def api_obtener_url():
    return jsonify({"result": request.host_url})

@app.route('/api/acortarUrl', methods=['GET'])
def api_acortar_url():
    url = request.args.get('arg0', '')
    url_corta = acortar_url(url)
    return jsonify({"result": url_corta})

@app.route('/api/getMarcasConDeuda', methods=['GET'])
def api_get_marcas_con_deuda():
    try:
        response = supabase.table('pedidos').select('marca_id, estado_pago, status').eq('estado_pago', 'Pendiente').neq('status', 'Cancelado').execute()
        marcas_ids = set()
        for p in response.data:
            if p.get('marca_id'):
                marcas_ids.add(p['marca_id'])
        
        if not marcas_ids:
            return jsonify({"result": []})
        
        marcas_response = supabase.table('marcas').select('id, nombre').in_('id', list(marcas_ids)).execute()
        marcas_nombres = sorted([m['nombre'] for m in marcas_response.data])
        
        return jsonify({"result": marcas_nombres})
    except Exception as e:
        return jsonify({"result": []})

# ==========================================
# 11. INICIAR SERVIDOR
# ==========================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 50)
    print("🚀 LUNA DELIVERY BACKEND (Flask + Supabase)")
    print(f"📍 Puerto: {port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=True)