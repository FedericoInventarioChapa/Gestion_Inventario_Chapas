import streamlit as st
import gspread
import pandas as pd
import json
from logic import SheetInventory

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Inventario de Chapas", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
def conectar_google_sheets():
    try:
        # Usamos el formato de json_data que configuramos en los Secrets
        info_json = st.secrets["gcp_service_account"]["json_data"]
        credentials = json.loads(info_json)
        gc = gspread.service_account_from_dict(credentials)
        # Asegúrate de que el nombre coincida con tu archivo
        return gc.open('Inventario Chapas').sheet1
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- INICIALIZACIÓN DEL ESTADO (Session State) ---
# Esto asegura que las variables no se borren al tocar botones
if 'inventory' not in st.session_state:
    st.session_state.inventory = {
        "T101 galvanizada": SheetInventory("T101 galvanizada"),
        "T101 zincalum": SheetInventory("T101 zincalum"),
        "Acanalada galvanizada": SheetInventory("Acanalada galvanizada"),
        "Acanalada zincalum": SheetInventory("Acanalada zincalum")
    }

if 'history' not in st.session_state:
    st.session_state.history = []  # <-- ESTA ES LA LÍNEA QUE FALTA O FALLA

# --- FUNCIONES DE PERSISTENCIA ---
def cargar_de_sheets():
    wks = conectar_google_sheets()
    if wks:
        data = wks.get_all_records()
        for row in data:
            nombre = row.get('TIPO_CHAPA')
            if nombre in st.session_state.inventory:
                obj = st.session_state.inventory[nombre]
                obj.full_sheets_count = int(row.get('CHAPAS_COMPLETAS', 0))
                cuts_str = str(row.get('RECORTES', ""))
                obj.cuts = [float(x) for x in cuts_str.split(',') if x.strip()]
        st.success("✅ Datos cargados desde Google Sheets")

def guardar_a_sheets():
    wks = conectar_google_sheets()
    if wks:
        rows = [["TIPO_CHAPA", "CHAPAS_COMPLETAS", "RECORTES"]]
        for name, obj in st.session_state.inventory.items():
            cuts_str = ",".join(map(str, obj.cuts))
            rows.append([name, obj.full_sheets_count, cuts_str])
        wks.update('A1', rows)
        st.success("💾 Inventario guardado en la nube")

# --- INTERFAZ ---
st.sidebar.header("Menú de Gestión")
opcion = st.sidebar.selectbox("Seleccione una operación", [
    "1. Mostrar Inventario", 
    "2. Añadir Stock", 
    "3. Tomar Material (Pedido)",
    "4. Sincronizar (Sheets)",
    "5. Historial de Cortes",
    "6. Descargar Reporte"
])

# PASO 1: MOSTRAR INVENTARIO
if opcion == "1. Mostrar Inventario":
    st.header("📋 Stock Actual")
    cols = st.columns(len(st.session_state.inventory))
    for i, (name, obj) in enumerate(st.session_state.inventory.items()):
        with cols[i]:
            st.subheader(name)
            st.metric("Completas", f"{obj.full_sheets_count} un.")
            st.write("**Recortes:**")
            st.write(obj.cuts if obj.cuts else "Vacio")

# PASO 3: TOMAR MATERIAL
elif opcion == "3. Tomar Material (Pedido)":
    st.header("✂️ Registrar Nuevo Corte")
    with st.form("form_corte"):
        tipo = st.selectbox("Chapa", list(st.session_state.inventory.keys()))
        largo = st.number_input("Largo (m)", min_value=0.5)
        cant = st.number_input("Cantidad", min_value=1, step=1)
        if st.form_submit_button("Procesar Corte"):
            exito, registros = st.session_state.inventory[tipo].take_material(largo, cant)
            if exito:
                st.session_state.history.extend(registros)
                st.success("Corte realizado.")
                guardar_a_sheets() # Automatización total
            else:
                st.error("No hay material suficiente.")

# PASO 4: SINCRONIZAR
elif opcion == "4. Sincronizar (Sheets)":
    st.header("🔄 Sincronización con Google")
    if st.button("Cargar datos ahora"):
        cargar_de_sheets()
    if st.button("Guardar datos ahora"):
        guardar_a_sheets()

# ... (puedes seguir agregando los demás pasos aquí)
