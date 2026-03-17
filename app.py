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
    "7. Buscador de Retazos"  # <-- Nueva opción añadida
])

# PASO 1: INVENTARIO con Alertas Visuales
if opcion == "1. Mostrar Inventario":
    st.header("📦 Stock en Depósito")
    
    for name, obj in st.session_state.inventory.items():
        # Lógica del semáforo
        cantidad = obj.full_sheets_count
        if cantidad <= 2:
            estado = "🚨 CRÍTICO"
            color_delta = "inverse"
        elif cantidad <= 5:
            estado = "⚠️ BAJO"
            color_delta = "normal"
        else:
            estado = "✅ OK"
            color_delta = "off"

        with st.expander(f"Ver {name}", expanded=True):
            col1, col2, col3 = st.columns([1, 1, 2])
            
            # Métrica principal con indicador de estado
            col1.metric("Chapas (13m)", f"{cantidad} un.", delta=estado, delta_color=color_delta)
            
            # Resumen de recortes
            clean_cuts = [round(c, 2) for c in obj.cuts]
            col2.metric("Recortes", f"{len(clean_cuts)} pzs")
            
            # Lista detallada
            col3.write(f"**Medidas disponibles (m):**")
            if clean_cuts:
                st.info(", ".join(map(str, sorted(clean_cuts, reverse=True))))
            else:
                st.caption("No hay recortes disponibles.")
            
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

# PASO 5: HISTORIAL Y REPORTES VISUALES
elif opcion == "5. Historial y Reporte":
    st.header("📊 Análisis de Ventas e Historial")
    
    if st.session_state.history:
        import pandas as pd
        
        # Convertimos el historial a un DataFrame de Pandas para manejar datos fácil
        df = pd.DataFrame(st.session_state.history)
        
        # --- FILA DE MÉTRICAS RÁPIDAS ---
        col1, col2, col3 = st.columns(3)
        total_metros = df[df['success'] == True]['length_requested'].sum()
        total_cortes = len(df)
        chapa_estrella = df['sheet_type'].mode()[0] if not df.empty else "N/A"
        
        col1.metric("Metros Cortados", f"{total_metros:.2f} m")
        col2.metric("Total de Piezas", f"{total_cortes} pzs")
        col3.metric("Chapa más vendida", chapa_estrella)

        st.divider()

        # --- GRÁFICOS ---
        tab1, tab2 = st.tabs(["📈 Gráficos de Rendimiento", "📋 Tabla de Datos"])
        
        with tab1:
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("Ventas por Tipo de Chapa")
                # Gráfico de torta simple de Streamlit
                chart_data = df.groupby('sheet_type')['length_requested'].sum()
                st.pie_chart(chart_data)
            
            with c2:
                st.subheader("Uso de Material")
                # Comparamos si sale de Chapa Completa o Recorte
                uso_data = df['source'].value_counts()
                st.bar_chart(uso_data)

        with tab2:
            st.subheader("Registro Detallado")
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
            
            # Botón para descargar CSV (por si lo quieres abrir en Excel)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Historial (Excel/CSV)",
                data=csv,
                file_name='historial_inventario.csv',
                mime='text/csv',
            )
    else:
        st.info("Aún no hay registros en el historial. ¡Empezá a cortar para ver las estadísticas!")

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
    st.header("🔍 Buscador de Piezas Sueltas")
    st.info("Usá esta herramienta para aprovechar sobrantes antes de tocar una chapa nueva.")
    
    c1, c2 = st.columns(2)
    with c1:
        tipo_b = st.selectbox("¿Qué chapa busca el cliente?", list(st.session_state.inventory.keys()))
    with c2:
        largo_b = st.number_input("Largo necesario (m)", min_value=0.5, step=0.1)

    lista_cortes = st.session_state.inventory[tipo_b].cuts
    min_reserva = 1.5
    
    candidatos = [
        c for c in lista_cortes 
        if c >= largo_b and (round(c - largo_b, 2) == 0 or round(c - largo_b, 2) >= min_reserva)
    ]
    candidatos.sort() 

    if candidatos:
        st.success(f"¡Encontramos {len(candidatos)} piezas que sirven!")
        for rec in candidatos[:3]: # <-- Corregido: 'in' en lugar de 'en'
            sobra = round(rec - largo_b, 2)
            st.warning(f"📏 **Pieza de {rec}m**: Si la cortás a {largo_b}m, te queda un sobrante de **{sobra}m**.")
            # Un pequeño aviso informativo
            st.caption(f"Si usás esta pieza, recordá cargar el pedido en 'Tomar Material' para descontarla.")
    else:
        st.error("No hay recortes que cumplan la regla de los 1.5m. Deberás usar una chapa de 13m.")
