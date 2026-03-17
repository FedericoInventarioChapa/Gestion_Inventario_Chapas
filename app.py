import streamlit as st
import gspread
import pandas as pd
import json
from logic import SheetInventory

st.set_page_config(page_title="Gestión de Chapas", layout="wide")

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

# --- MENÚ LATERAL ---
opcion = st.sidebar.radio("Operaciones:", [
    "1. Mostrar Inventario", 
    "2. Añadir Stock", 
    "3. Tomar Material",
    "4. Deshacer Pedido",
    "5. Historial y Reporte",
    "6. Sincronizar Google Sheets"
])

# PASO 1: INVENTARIO
if opcion == "1. Mostrar Inventario":
    st.header("📦 Stock en Depósito")
    for name, obj in st.session_state.inventory.items():
        with st.expander(f"Ver {name}", expanded=True):
            c1, c2 = st.columns(2)
            c1.metric("Chapas (13m)", f"{obj.full_sheets_count} un.")
            # Limpiamos visualmente la lista de recortes para que no haya errores de redondeo
            clean_cuts = [round(c, 2) for c in obj.cuts]
            c2.write(f"**Recortes Disponibles:** {clean_cuts if clean_cuts else 'Sin recortes'}")

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
    st.warning("⚠️ Regla: Sobrantes menores a 1.50m serán bloqueados o descartados.")
    
    with st.form("corte_form"):
        cliente = st.text_input("Nombre del Cliente / Orden #", placeholder="Ej: Juan Pérez")
        tipo = st.selectbox("Chapa", list(st.session_state.inventory.keys()))
        largo = st.number_input("Largo del corte (m)", min_value=0.5, max_value=11.5, step=0.1)
        cant = st.number_input("Cantidad de piezas", min_value=1, step=1)
        
        if st.form_submit_button("Procesar y Generar Orden"):
            if not cliente:
                st.error("Por favor, ingresa el nombre del cliente.")
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
                    
                    resumen_texto = f"*CLIENTE:* {cliente}\n*PRODUCTO:* {tipo}\n"
                    resumen_texto += "-"*20 + "\n"

                    for i, r in enumerate(registros):
                        origen = r['source']
                        # Calculamos el largo original para el operario
                        largo_original = round(r['length_requested'] + r['remnant'], 2) if origen == 'Recorte' else 13.0
                        
                        detalle = f"PIEZA {i+1}: Corte de {largo}m\n👉 EXTRAER DE: {origen} (Medida: {largo_original}m)\n"
                        st.info(detalle)
                        resumen_texto += detalle + "\n"
                    
                    st.code(resumen_texto, language="text")

                    # --- BOTÓN DE WHATSAPP ---
                    import urllib.parse
                    # Puedes cambiar este número por el del cortador
                    tel = "5491122334455" 
                    texto_url = urllib.parse.quote(resumen_texto)
                    link_wa = f"https://wa.me/{tel}?text={texto_url}"
                    st.link_button("📲 Enviar Orden al Cortador", link_wa)
                else:
                    if registros and "error" in registros[0]:
                        st.error(registros[0]["error"])
                    else:
                        st.error("Stock insuficiente para cumplir la regla de 1.5m.")
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
