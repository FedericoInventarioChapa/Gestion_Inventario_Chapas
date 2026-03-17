import streamlit as st
import gspread
import pandas as pd
import json
from logic import SheetInventory

st.set_page_config(page_title="Gestión de Chapas", layout="wide")

def obtener_contactos_sheets():
    try:
        doc = conectar_google_sheets()
        if doc:
            # Intentamos abrir la pestaña 'Contactos'
            wks_contactos = doc.worksheet('Contactos')
            datos = wks_contactos.get_all_records()
            # Convertimos a un diccionario {Nombre: Telefono}
            return {str(fila['NOMBRE']): str(fila['TELEFONO']) for fila in datos if fila['NOMBRE']}
    except Exception as e:
        st.error(f"No se pudo cargar la agenda: {e}")
    return {"Sin Contactos": ""}

# --- CONEXIÓN SEGURA ---
def conectar_google_sheets():
    try:
        info_json = st.secrets["gcp_service_account"]["json_data"]
        credentials = json.loads(info_json)
        gc = gspread.service_account_from_dict(credentials)
        return gc.open('Inventario Chapas')
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- FUNCIONES DE GUARDADO AUTOMÁTICO ---
def guardar_stock_actual():
    doc = conectar_google_sheets()
    if doc:
        wks = doc.sheet1
        rows = [["TIPO_CHAPA", "CHAPAS_COMPLETAS", "RECORTES"]]
        for name, obj in st.session_state.inventory.items():
            cuts_str = ",".join(map(str, obj.cuts))
            rows.append([name, obj.full_sheets_count, cuts_str])
        
        wks.clear()
        wks.update('A1', rows)

def registrar_en_historial_sheets(registros):
    try:
        doc = conectar_google_sheets()
        if doc:
            try:
                wks_historial = doc.worksheet('Historial')
            except:
                wks_historial = doc.add_worksheet(title="Historial", rows="1000", cols="10")
                wks_historial.append_row(["Fecha", "Cliente", "Chapa", "Largo", "Origen", "Sobrante"])

            filas_nuevas = []
            for r in registros:
                filas_nuevas.append([
                    r['timestamp'], 
                    r.get('cliente', 'S/N'), 
                    r['sheet_type'], 
                    r['length_requested'], 
                    r['source'], 
                    r['remnant']
                ])
            wks_historial.append_rows(filas_nuevas)
    except Exception as e:
        st.error(f"Error al guardar historial: {e}")

# --- INICIALIZACIÓN ---
if 'inventory' not in st.session_state:
    st.session_state.inventory = {
        "T101 galvanizada": SheetInventory("T101 galvanizada"),
        "T101 zincalum": SheetInventory("T101 zincalum"),
        "Acanalada galvanizada": SheetInventory("Acanalada galvanizada"),
        "Acanalada zincalum": SheetInventory("Acanalada zincalum")
    }
if 'history' not in st.session_state:
    st.session_state.history = []

opcion = st.sidebar.radio("Operaciones:", [
    "1. Mostrar Inventario", 
    "2. Añadir Stock", 
    "3. Tomar Material",
    "4. Deshacer Pedido",
    "5. Historial y Reporte",
    "6. Sincronizar Google Sheets",
    "7. Buscador de Retazos" # <-- Nueva opción
])

# PASO 1: INVENTARIO con Semáforo
if opcion == "1. Mostrar Inventario":
    st.header("📦 Stock en Depósito")
    for name, obj in st.session_state.inventory.items():
        # Definimos el color según la cantidad
        if obj.full_sheets_count <= 2:
            color = "inverse" # Rojo/Crítico
            mensaje = "🚨 STOCK CRÍTICO: Reponer urgente"
        elif obj.full_sheets_count <= 5:
            color = "normal" 
            mensaje = "⚠️ STOCK BAJO: Considerar compra"
        else:
            color = "off"
            mensaje = "✅ Stock Saludable"

        with st.expander(f"Ver {name}", expanded=True):
            c1, c2, c3 = st.columns([1, 1, 2])
            c1.metric("Chapas (13m)", f"{obj.full_sheets_count} un.", delta=mensaje if obj.full_sheets_count <= 5 else None, delta_color="normal")
            
            clean_cuts = [round(c, 2) for c in obj.cuts]
            c2.metric("Total Recortes", f"{len(clean_cuts)} piezas")
            c3.write(f"**Medidas disponibles:** {clean_cuts if clean_cuts else 'Sin recortes'}")
            
# PASO 2: AÑADIR STOCK
elif opcion == "2. Añadir Stock":
    st.header("➕ Ingreso de Material")
    with st.form("add_form"):
        tipo_add = st.selectbox("Tipo de chapa", list(st.session_state.inventory.keys()))
        cantidad_add = st.number_input("Cantidad de chapas de 13m", min_value=1, step=1)
        if st.form_submit_button("Añadir al Inventario"):
            st.session_state.inventory[tipo_add].add_full_sheets(cantidad_add)
            guardar_stock_actual() 
            st.success(f"Se agregaron {cantidad_add} chapas a {tipo_add} y se guardó en la nube.")

# PASO 3: TOMAR MATERIAL
elif opcion == "3. Tomar Material":
    st.header("✂️ Registro de Corte para Producción")
    
    # --- CARGA DE AGENDA DINÁMICA ---
    agenda = obtener_contactos_sheets()
    
    col_tel, col_info = st.columns(2)
    with col_tel:
        nombre_cortador = st.selectbox("📲 Seleccionar Cortador:", list(agenda.keys()))
        tel_destino = agenda[nombre_cortador]
    
    with col_info:
        st.info(f"Enviar a: {nombre_cortador} ({tel_destino})")

    st.warning("⚠️ Regla: Sobrantes menores a 1.50m serán bloqueados o descartados.")
    
    with st.form("corte_form"):
        cliente = st.text_input("Nombre del Cliente / Orden #", placeholder="Ej: Juan Pérez")
        tipo = st.selectbox("Chapa", list(st.session_state.inventory.keys()))
        largo = st.number_input("Largo del corte (m)", min_value=0.5, max_value=11.5, step=0.1)
        cant = st.number_input("Cantidad de piezas", min_value=1, step=1)
        
        if st.form_submit_button("Procesar y Generar Orden"):
            if not cliente:
                st.error("Por favor, ingresa el nombre del cliente.")
            elif not tel_destino:
                st.error("El contacto seleccionado no tiene un teléfono válido.")
            else:
                exito, registros = st.session_state.inventory[tipo].take_material(largo, cant)
                if exito:
                    for r in registros:
                        r['cliente'] = cliente
                    
                    st.session_state.history.extend(registros)
                    registrar_en_historial_sheets(registros)
                    guardar_stock_actual()

                    st.success(f"✅ Pedido registrado para {cliente}")
                    st.markdown("### 📝 Hoja de Corte (Producción)")
                    
                    # Formateamos el mensaje para WhatsApp
                    resumen_texto = f"*ORDEN DE CORTE*\n"
                    resumen_texto += f"*CLIENTE:* {cliente}\n"
                    resumen_texto += f"*PRODUCTO:* {tipo}\n"
                    resumen_texto += "-"*20 + "\n"

                    for i, r in enumerate(registros):
                        origen = r['source']
                        largo_original = round(r['length_requested'] + r['remnant'], 2) if origen == 'Recorte' else 13.0
                        detalle = f"PIEZA {i+1}: Corte de {largo}m\n👉 EXTRAER DE: {origen} ({largo_original}m)\n"
                        st.info(detalle)
                        resumen_texto += detalle + "\n"
                    
                    st.code(resumen_texto, language="text")

                    # --- BOTÓN DE WHATSAPP ---
                    import urllib.parse
                    texto_url = urllib.parse.quote(resumen_texto)
                    link_wa = f"https://wa.me/{tel_destino}?text={texto_url}"
                    st.link_button(f"📲 Enviar Orden a {nombre_cortador}", link_wa)
                else:
                    if registros and "error" in registros[0]:
                        st.error(registros[0]["error"])
                    else:
                        st.error("Stock insuficiente.")
# PASO 4: DESHACER
elif opcion == "4. Deshacer Pedido":
    st.header("↩️ Deshacer Último Movimiento")
    if st.session_state.history:
        ultimo = st.session_state.history[-1]
        st.write(f"Último registro: **{ultimo['sheet_type']}** de **{ultimo['length_requested']}m** para **{ultimo.get('cliente','S/N')}**")
        if st.button("Confirmar y Restaurar Stock"):
            st.session_state.inventory[ultimo['sheet_type']].undo_cut(ultimo['source'], ultimo['length_requested'], ultimo['remnant'])
            st.session_state.history.pop()
            guardar_stock_actual() 
            st.success("Operación deshecha y stock restaurado.")
            st.rerun()
    else:
        st.info("No hay nada para deshacer.")

# PASO 5: HISTORIAL
elif opcion == "5. Historial y Reporte":
    st.header("📜 Historial de Pedidos")
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        columnas = ['timestamp', 'cliente', 'sheet_type', 'length_requested', 'source', 'remnant']
        df = df[[c for c in columnas if c in df.columns]]
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV", csv, "produccion.csv", "text/csv")

# PASO 6: SINCRONIZACIÓN MANUAL
elif opcion == "6. Sincronizar Google Sheets":
    st.header("🔄 Sincronización Manual")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Cargar desde Sheets"):
            doc = conectar_google_sheets()
            if doc:
                data = doc.sheet1.get_all_records()
                for row in data:
                    nombre = row.get('TIPO_CHAPA')
                    if nombre in st.session_state.inventory:
                        obj = st.session_state.inventory[nombre]
                        obj.full_sheets_count = int(row.get('CHAPAS_COMPLETAS', 0))
                        cuts_str = str(row.get('RECORTES', ""))
                        obj.cuts = [float(x.strip()) for x in cuts_str.split(',') if x.strip()]
                st.success("✅ Stock cargado.")
                st.rerun()
    with col2:
        if st.button("📤 Guardar en Sheets"):
            guardar_stock_actual()
            st.success("💾 Stock guardado.")

# PASO 7: BUSCADOR DE RETAZOS
elif opcion == "7. Buscador de Retazos":
    st.header("🔍 Buscador Rápido de Recortes")
    st.write("Usá esta herramienta para encontrar piezas sueltas que le sirvan a un cliente sin tocar las chapas de 13m.")
    
    col1, col2 = st.columns(2)
    with col1:
        tipo_busqueda = st.selectbox("Tipo de chapa", list(st.session_state.inventory.keys()))
    with col2:
        medida_buscada = st.number_input("¿Qué largo busca el cliente? (m)", min_value=0.5, step=0.1)
    
    recortes_vivos = st.session_state.inventory[tipo_busqueda].cuts
    # Filtramos los que sirven
    sirven = [c for c in recortes_vivos if c >= medida_buscada]
    sirven.sort() # Los ordenamos de menor a mayor
    
    if sirven:
        st.success(f"Encontramos {len(sirven)} recortes que sirven.")
        # Mostramos los mejores 3 para no desperdiciar
        for r in sirven[:3]:
            sobrante_final = round(r - medida_buscada, 2)
            st.info(f"📏 Recorte de **{r}m** -> Si lo cortás, te sobran **{sobrante_final}m**.")
    else:
        st.error("No hay ningún recorte de ese largo. Vas a tener que usar una Chapa Completa.")
