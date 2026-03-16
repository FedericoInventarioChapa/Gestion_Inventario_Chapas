import json # Agregamos esto arriba de todo

def conectar_google_sheets():
    # Leemos el JSON como un texto largo y lo convertimos a diccionario
    info_json = st.secrets["gcp_service_account"]["json_data"]
    credentials = json.loads(info_json)
    
    gc = gspread.service_account_from_dict(credentials)
    # Asegúrate de que el nombre coincida con tu archivo de Google Sheets
    return gc.open('Inventario Chapas').sheet1
import streamlit as st
import gspread
import pandas as pd
from logic import SheetInventory # Importamos tu "cerebro"

# --- CONFIGURACIÓN DE CONEXIÓN SEGURA ---
def conectar_google_sheets():
    # Streamlit leerá los datos del JSON desde una "caja fuerte" llamada secrets
    credentials = st.secrets["gcp_service_account"]
    gc = gspread.service_account_from_dict(credentials)
    # Cambia 'Inventario Chapas' por el nombre exacto de tu Google Sheet si es diferente
    return gc.open('Inventario Chapas').sheet1

# --- INICIALIZACIÓN DEL ESTADO ---
if 'inventory' not in st.session_state:
    # Creamos el inventario vacío
    st.session_state.inventory = {
        "T101 galvanizada": SheetInventory("T101 galvanizada"),
        "T101 zincalum": SheetInventory("T101 zincalum"),
        "Acanalada galvanizada": SheetInventory("Acanalada galvanizada"),
        "Acanalada zincalum": SheetInventory("Acanalada zincalum")
    }
    # Intentamos cargar datos desde Sheets al arrancar
    try:
        wks = conectar_google_sheets()
        data = wks.get_all_records()
        for row in data:
            nombre = row['TIPO_CHAPA']
            if nombre in st.session_state.inventory:
                obj = st.session_state.inventory[nombre]
                obj.full_sheets_count = int(row['CHAPAS_COMPLETAS'])
                cuts_str = str(row['RECORTES'])
                obj.cuts = [float(x) for x in cuts_str.split(',') if x.strip()]
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")

# --- INTERFAZ (FRONTEND) ---
st.title("📦 Sistema de Inventario de Chapas")

menu = ["Inventario Actual", "Añadir Stock", "Registrar Corte", "Historial"]
choice = st.sidebar.selectbox("Menú Principal", menu)

if choice == "Inventario Actual":
    st.header("Stock en Depósito")
    for name, obj in st.session_state.inventory.items():
        with st.expander(f"Chapa: {name}"):
            col1, col2 = st.columns(2)
            col1.metric("Chapas Completas", f"{obj.full_sheets_count} un.")
            col2.write("**Recortes disponibles:**")
            col2.write(obj.cuts if obj.cuts else "No hay recortes.")

elif choice == "Registrar Corte":
    st.header("Nuevo Pedido de Corte")
    with st.form("form_corte"):
        tipo = st.selectbox("Seleccione Chapa", list(st.session_state.inventory.keys()))
        largo = st.number_input("Largo necesario (metros)", min_value=0.5, step=0.1)
        cantidad = st.number_input("Cantidad de cortes", min_value=1, step=1)
        
        if st.form_submit_button("Procesar y Guardar"):
            exito, registros = st.session_state.inventory[tipo].take_material(largo, cantidad)
            if exito:
                st.success("¡Corte registrado con éxito!")
                # Aquí llamaríamos a una función para guardar en Sheets (la haremos en el siguiente paso)
            else:
                st.error("Material insuficiente para completar el pedido.")
