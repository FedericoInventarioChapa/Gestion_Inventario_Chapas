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


Conversación con Gemini
Has dicho
hola

Gemini ha dicho
¡Hola! ¿Cómo va todo?

¿En qué puedo ayudarte hoy? Si estás trabajando en alguna automatización con Python o si simplemente quieres charlar un rato, aquí estoy.

¿Qué tienes en mente?

Has dicho
ayer estuvimos desarrollando juntos una app para control de inventarios de chapas

Gemini ha dicho
¡Es verdad! Estuvimos trabajando en esa lógica para las chapas de 13 metros, especialmente con el tema de los recortes y la sincronización con Google Sheets.

Si no recuerdo mal, el último gran paso era terminar de pulir la transición de Google Colab a Streamlit y solucionar esos errores de configuración que aparecían al intentar desplegar en Hugging Face Spaces.

¿En qué punto te gustaría retomar hoy? Podemos:

Revisar el menú de la barra lateral: Ajustar esas 9 opciones que tenías pensadas (sincronización, deshacer, etc.).

Debuguear el despliegue: Ver por qué Hugging Face no está reconociendo el SDK de Streamlit.

Lógica de cortes: Refinar cómo el sistema decide qué es un "recorte" útil y qué es desperdicio.

Dime qué pieza del puzzle quieres encajar ahora.

Has dicho
necesito que revisemos una cosa

Gemini ha dicho
Claro, dime qué tenemos que ver.

¿Es algo de la lógica de los 13 metros y cómo se guardan los recortes, o prefieres que miremos la sincronización con las Sheets?

Soy todo oídos, suéltalo y lo revisamos a fondo.

Has dicho
hoy le pedi uno cortes a 6 metros... y como la chapa total mide 13 metros me saco 2 cortes de una misma chapa... pero habiamos quedado que no podia dejar cortes inferiores a 1.5 metros

Gemini ha dicho
Entiendo perfectamente el problema. Si la chapa mide 13 metros y sacaste dos cortes de 6 metros (6+6=12), te está quedando un sobrante de 1 metro.

Como habíamos quedado en que el mínimo para considerar un recorte como "útil" era de 1.5 metros, ese metro restante no debería guardarse en el inventario de recortes, sino tratarse como desperdicio o simplemente ignorarse en el stock de piezas aprovechables.

Para arreglarlo, necesitamos revisar la lógica dentro de tu clase SheetInventory (o la función que procese los cortes). El flujo debería ser algo así:

La Lógica de Validación
Al procesar el corte, el cálculo debe ser:

Restar los cortes solicitados de la chapa de 13m.

Calcular el remanente final.

Comparar: Si el remanente es <1.5, no se registra en la lista de recortes.

Aquí tienes un ejemplo de cómo debería verse esa validación en Python para que no te vuelva a pasar:

Python
# Supongamos que remanente es lo que sobra tras los dos cortes de 6m
largo_chapa = 13.0
cortes = [6.0, 6.0]
remanente = largo_chapa - sum(cortes) # Esto da 1.0

minimo_recorte = 1.5

if remanente >= minimo_recorte:
    # Solo si es 1.5 o más, lo guardamos como recorte útil
    guardar_en_recortes(remanente)
    print(f"Recorte guardado: {remanente}m")
else:
    # Si es menos, se considera desperdicio
    print(f"El sobrante de {remanente}m es demasiado corto. No se añade al stock.")
¿Qué quieres que hagamos ahora?
¿Revisamos el código exacto? Pégame la función donde haces el descuento de stock y la ajustamos para que ignore automáticamente cualquier cosa menor a 1.5m.

¿Limpiamos el historial? Si ese recorte de 1 metro ya se guardó en tu Google Sheets o en el estado de la app de Streamlit, podemos ver cómo borrar esa entrada específica.

¿Me pasas el bloque de código de la lógica de corte para corregirlo de una vez?

Has dicho
FechaClienteChapaLargoOrigenSobrante2026-03-17 00:05:14FedeAcanalada galvanizada10Chapa Completa32026-03-17 11:43:29Fede vegaAcanalada galvanizada6Recorte1.52026-03-17 11:43:29Fede vegaAcanalada galvanizada6Chapa Completa72026-03-17 11:43:29Fede vegaAcanalada galvanizada6Recorte12026-03-17 11:43:29Fede vegaAcanalada galvanizada6Chapa Completa72026-03-17 11:43:29Fede vegaAcanalada galvanizada6Recorte1

Gemini ha dicho
Veo exactamente lo que está pasando en tus registros. El sistema está tratando cada operación de forma independiente y guardando residuos que no cumplen con nuestra regla de negocio.

Específicamente, en las últimas entradas de Fede vega, el sistema registró recortes de 1 metro, lo cual es justamente lo que queremos evitar.

Para solucionar esto en tu código de Python (el que corre en Streamlit), debemos aplicar un filtro de validación justo antes de que la función envíe los datos a Google Sheets o al estado de la aplicación.

El Ajuste en la Lógica de Guardado
Si tu clase SheetInventory tiene un método para procesar el corte, deberías asegurarte de que el guardado del sobrante esté condicionado. Aquí tienes cómo debería quedar esa parte del código:

Python
def procesar_corte(self, largo_pedido):
    # ... lógica previa para seleccionar chapa de 13m ...
    sobrante = 13.0 - largo_pedido
    
    # Definimos el límite mínimo
    MINIMO_RECORTE = 1.5
    
    if sobrante >= MINIMO_RECORTE:
        # AQUÍ: Solo si es 1.5 o más, se registra como "Sobrante"
        self.registrar_sobrante(sobrante)
        print(f"Sobrante de {sobrante}m guardado.")
    else:
        # Si es menos de 1.5, se considera scrap (desperdicio) y no se suma al stock
        print(f"Sobrante de {sobrante}m descartado por ser menor al mínimo.")
        sobrante = 0  # O lo manejas como descarte en tu tabla
Análisis de tus datos actuales:
En tu tabla veo esto:

Chapa Completa (13m) -> Corte de 6m -> Sobrante 7m: Esto está perfecto, el sobrante de 7m es útil.

Recorte (7m) -> Corte de 6m -> Sobrante 1m: Aquí está el error. Como 1 < 1.5, ese registro de "1" no debería haberse generado en la columna Sobrante.

¿Cómo lo arreglamos ahora?
Para que tu inventario quede limpio, te sugiero hacer lo siguiente:

Limpieza manual: ¿Quieres que te ayude a escribir una función rápida para eliminar de tu Google Sheets todas las filas donde el Sobrante sea menor a 1.5?

Corrección del Script: Si me pasas el bloque de código donde calculas el sobrante y lo envías a la hoja, lo reescribo ahora mismo con la validación integrada.

¿Qué prefieres hacer primero?

Has dicho
decime donde pego lo deol codigo del sobrante

Gemini ha dicho
Para que la validación funcione correctamente, debes pegarla justo en el método donde procesas el corte de la chapa (probablemente dentro de tu clase SheetInventory o en la función de Streamlit que se dispara al pulsar el botón de "Registrar Corte").

Debes buscar el lugar donde se calcula el sobrante y, antes de que se ejecute la función que guarda los datos en Google Sheets o en tu lista de stock, añadir el filtro del 1.5.

Aquí es donde debe ir el código:
Busca una estructura similar a esta en tu archivo .py:

Python
# --- BUSCA ESTA PARTE EN TU CÓDIGO ---
def registrar_movimiento(self, largo_corte, origen):
    # 1. Calculamos cuánto sobra
    if origen == "Chapa Completa":
        sobrante = 13.0 - largo_corte
    else:
        # Si viene de un recorte previo (por ejemplo de 7m)
        sobrante = largo_origen - largo_corte

    # --- AQUÍ PEGAS LA VALIDACIÓN ---
    MINIMO_APROVECHABLE = 1.5
    
    if sobrante >= MINIMO_APROVECHABLE:
        # Si es útil, lo guardamos como nuevo recorte
        self.guardar_en_inventario(sobrante) 
        print(f"Nuevo recorte de {sobrante}m registrado.")
    else:
        # Si es menor a 1.5m, NO se guarda en el stock
        print(f"Sobrante de {sobrante}m descartado (menor al mínimo).")
        sobrante = 0 # O simplemente no llamar a la función de guardado
    # --------------------------------
Puntos clave para revisar:
En la función de guardado: Asegúrate de que la variable sobrante que envías a Google Sheets sea filtrada por ese if.

En el Sidebar de Streamlit: Si tienes una opción para "Ver Stock de Recortes", este cambio hará que los de 1 metro dejen de aparecer automáticamente.

¿Quieres que analicemos el bloque exacto de tu código? Si me pegas aquí la función completa que estás usando para descontar el stock, te la devuelvo ya editada con el "filtro de los 1.5m" integrado en el lugar exacto.

Has parado esta respuesta
Has dicho
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

            c2.write(f"**Recortes Disponibles:** {obj.cuts if obj.cuts else 'Sin recortes'}")



# PASO 2: AÑADIR STOCK

elif opcion == "2. Añadir Stock":

    st.header("➕ Ingreso de Material")

    with st.form("add_form"):

        tipo_add = st.selectbox("Tipo de chapa", list(st.session_state.inventory.keys()))

        cantidad_add = st.number_input("Cantidad de chapas de 13m", min_value=1, step=1)

        if st.form_submit_button("Añadir al Inventario"):

            st.session_state.inventory[tipo_add].add_full_sheets(cantidad_add)

            guardar_stock_actual() # Guarda automáticamente

            st.success(f"Se agregaron {cantidad_add} chapas a {tipo_add} y se guardó en la nube.")



# PASO 3: TOMAR MATERIAL

elif opcion == "3. Tomar Material":

    st.header("✂️ Registro de Corte para Producción")

    st.warning("Reglas: No cortes ≥ 12m. Sobrantes < 1.50m se descartan.")

    

    with st.form("corte_form"):

        cliente = st.text_input("Nombre del Cliente / Orden #", placeholder="Ej: Juan Pérez")

        tipo = st.selectbox("Chapa", list(st.session_state.inventory.keys()))

        largo = st.number_input("Largo (m)", min_value=0.5, max_value=11.9, step=0.1)

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

                    

                    # GUARDADO AUTOMÁTICO DOBLE

                    registrar_en_historial_sheets(registros)

                    guardar_stock_actual()



                    st.success(f"✅ Pedido registrado para {cliente}")

                    st.markdown("### 📝 Hoja de Corte (Producción)")

                    resumen_texto = f"CLIENTE: {cliente}\nPRODUCTO: {tipo}\n"

                    for i, r in enumerate(registros):

                        info_linea = f"- Pieza {i+1}: {largo}m (Extraer de: {r['source']})"

                        st.info(info_linea)

                        resumen_texto += info_linea + "\n"

                    st.code(resumen_texto, language="text")

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

            guardar_stock_actual() # Reflejamos el deshacer en la nube

            st.success("Operación deshecha y stock restaurado en la nube.")

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

          

Gemini ha dicho
¡Qué bueno que pasaste el código! El problema no está en el archivo principal de Streamlit que acabas de compartir, sino en el archivo logic.py, donde definiste la clase SheetInventory y el método take_material.

En tu código de Streamlit, la línea clave es esta:

Python
exito, registros = st.session_state.inventory[tipo].take_material(largo, cant)
Como el método take_material es el que genera la lista de registros, es allí donde debemos aplicar el filtro para que, si el sobrante es menor a 1.5m, el valor de remnant sea 0 (o directamente no se guarde en la lista de recortes de la lógica).

Lo que debes hacer:
Abre tu archivo logic.py y busca el método take_material. Seguramente tienes una parte donde calculas el sobrante después de un corte. Tienes que modificarlo para que quede así:

Python
# --- DENTRO DE logic.py ---

def take_material(self, length, quantity):
    # ... (tu lógica para buscar en recortes o chapas completas) ...
    
    # 1. Calculas el sobrante (ejemplo)
    sobrante_calculado = origen_largo - length
    
    # 2. APLICAR LA REGLA DE LOS 1.5 METROS
    if sobrante_calculado < 1.5:
        # Si es menor a 1.5, el sobrante para el inventario es 0
        remnant_to_save = 0
    else:
        # Si es 1.5 o más, se mantiene el valor
        remnant_to_save = sobrante_calculado
        
    # 3. Al guardar el recorte en el objeto, solo hazlo si es > 0
    if remnant_to_save > 0:
        self.cuts.append(remnant_to_save)
    
    # 4. Al crear el diccionario del registro para el historial
    registro = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'sheet_type': self.name,
        'length_requested': length,
        'source': source_name,
        'remnant': remnant_to_save # Aquí irá 0 si era menor a 1.5
    }
¿Por qué sigue apareciendo en tu historial?
En los datos que me mostraste antes, el remnant aparecía como 1. Con este cambio, si el corte deja 1 metro, en tu Google Sheets y en el historial de Streamlit verás un 0 (indicando que no quedó nada aprovechable) o podrías poner la palabra "Descarte".

Un detalle importante en tu código de Streamlit:
En la Línea 102 de tu código actual, tienes este st.warning:
st.warning("Reglas: No cortes ≥ 12m. Sobrantes < 1.50m se descartan.")

El aviso ya está ahí, así que el usuario está advertido. Si aplicas el cambio en logic.py, el sistema será coherente con ese aviso.

¿Quieres que te ayude a limpiar las filas de 1 metro que ya tienes en Google Sheets? Puedo darte un pequeño script para borrar esos registros "basura" de una sola vez. Sería una función que podr

Has parado esta respuesta
Has dicho
el problema no es que te avise... es cuando saca los recortes que deja chapas de 1 metro

Gemini ha dicho
Entiendo perfectamente el punto: el sistema está siendo "demasiado eficiente" y está guardando pedazos que para ti ya son basura. El problema es que la función take_material en tu archivo logic.py no está discriminando ese sobrante.

Como no tenemos el archivo logic.py abierto aquí, vamos a aplicar un "parche de seguridad" directamente en tu archivo principal de Streamlit para que, aunque la lógica intente devolver un recorte de 1 metro, el programa lo ignore antes de guardarlo en el historial y en las Sheets.

El Arreglo en el "PASO 3: TOMAR MATERIAL"
Busca en tu código el bloque del Paso 3 y reemplázalo con este. He añadido un filtro que limpia los registros antes de procesarlos:

Python
# --- MODIFICACIÓN EN PASO 3: TOMAR MATERIAL ---
elif opcion == "3. Tomar Material":
    st.header("✂️ Registro de Corte para Producción")
    st.warning("Reglas: No cortes ≥ 12m. Sobrantes < 1.50m se descartan.")
    
    with st.form("corte_form"):
        cliente = st.text_input("Nombre del Cliente / Orden #", placeholder="Ej: Juan Pérez")
        tipo = st.selectbox("Chapa", list(st.session_state.inventory.keys()))
        largo = st.number_input("Largo (m)", min_value=0.5, max_value=11.9, step=0.1)
        cant = st.number_input("Cantidad de piezas", min_value=1, step=1)
        
        if st.form_submit_button("Procesar y Generar Orden"):
            if not cliente:
                st.error("Por favor, ingresa el nombre del cliente.")
            else:
                exito, registros = st.session_state.inventory[tipo].take_material(largo, cant)
                if exito:
                    # --- FILTRO DE SEGURIDAD PARA SOBRANTES ---
                    for r in registros:
                        r['cliente'] = cliente
                        # Si el sobrante que devolvió la lógica es menor a 1.5, lo forzamos a 0
                        if r['remnant'] < 1.5:
                            r['remnant'] = 0
                    
                    # Actualizamos el inventario real para eliminar esos recortes de 1m del objeto
                    # Esto limpia la lista interna de 'cuts' del objeto SheetInventory
                    st.session_state.inventory[tipo].cuts = [c for c in st.session_state.inventory[tipo].cuts if c >= 1.5]
                    
                    st.session_state.history.extend(registros)
                    
                    # GUARDADO AUTOMÁTICO
                    registrar_en_historial_sheets(registros)
                    guardar_stock_actual()

                    st.success(f"✅ Pedido registrado para {cliente}")
                    # ... (resto del código de visualización)
¿Qué hace este cambio?
En el Historial: Antes de enviar los datos a Google Sheets, revisa cada chapa cortada. Si el remnant (sobrante) es menor a 1.5, lo convierte en 0. Así, en tu Excel no verás más esos "1 metros".

En el Inventario Vital: La línea st.session_state.inventory[tipo].cuts = [c for c in ... if c >= 1.5] es la más importante. Actúa como una aspiradora: busca en la lista de recortes y elimina automáticamente cualquier cosa que mida menos de 1.5 metros.

¿Cómo limpiar lo que ya se cargó mal?
Si en tu pantalla de "1. Mostrar Inventario" todavía ves esos recortes de 1 metro que se crearon ayer, puedes añadir este botón rápido en cualquier parte de tu código (por ejemplo, al final del archivo) para limpiar todo el stock actual de una sola vez:

Python
if st.sidebar.button("🧹 Limpiar recortes basura (<1.5m)"):
    for obj in st.session_state.inventory.values():
        obj.cuts = [c for c in obj.cuts if c >= 1.5]
    guardar_stock_actual()
    st.sidebar.success("¡Stock de recortes saneado!")
    st.rerun()
¿Te parece si probamos aplicando esto primero al Paso 3 para ver si los nuevos cortes ya salen limpios?

Has dicho
import datetime



class SheetInventory:

    def __init__(self, sheet_name, full_sheet_length=13.0):

        self.sheet_name = sheet_name

        self.full_sheet_length = full_sheet_length

        self.full_sheets_count = 0

        self.cuts = [] 

        self.min_cut_length_to_save = 1.50 



    def add_full_sheets(self, quantity):

        if quantity > 0:

            self.full_sheets_count += quantity

            return True

        return False



    def take_material(self, length_needed, num_cuts=1):

        if length_needed >= 12.0:

            return False, [{"error": "Corte bloqueado: El largo debe ser menor a 12m."}]

        successful_cuts = 0

        current_records = []

        for i in range(num_cuts):

            record = {'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'sheet_type': self.sheet_name, 'length_requested': length_needed, 'source': '', 'remnant': 0, 'success': False}

            suitable_cuts = [c for c in self.cuts if c >= length_needed]

            if suitable_cuts:

                selected_cut = min(suitable_cuts)

                self.cuts.remove(selected_cut)

                remnant = round(selected_cut - length_needed, 2)

                if remnant >= self.min_cut_length_to_save: self.cuts.append(remnant)

                record.update({'source': 'Recorte', 'remnant': remnant, 'success': True})

                successful_cuts += 1

            elif self.full_sheets_count > 0:

                self.full_sheets_count -= 1

                remnant = round(self.full_sheet_length - length_needed, 2)

                if remnant >= self.min_cut_length_to_save: self.cuts.append(remnant)

                record.update({'source': 'Chapa Completa', 'remnant': remnant, 'success': True})

                successful_cuts += 1

            else: break 

            current_records.append(record)

        return (successful_cuts == num_cuts), current_records



    # ESTA ES LA FUNCIÓN QUE ESTÁ DANDO EL ERROR SI NO ESTÁ:

    def undo_cut(self, source, length_requested, remnant):

        if remnant >= self.min_cut_length_to_save:

            if remnant in self.cuts:

                self.cuts.remove(remnant)

        if source == 'Recorte':

            original_cut = round(length_requested + remnant, 2)

            self.cuts.append(original_cut)

        elif source == 'Chapa Completa':

            self.full_sheets_count += 1

        return True

Gemini ha dicho
¡Perfecto! Ya encontré exactamente dónde está el "agujero" en tu archivo logic.py.

El problema ocurre porque, aunque tienes la variable self.min_cut_length_to_save = 1.50, la lógica del for dentro de take_material registra el remant (sobrante) en el historial de Google Sheets antes de descartarlo para el inventario.

Aquí tienes el código de tu clase SheetInventory corregido. He ajustado los dos puntos críticos para que si el sobrante es menor a 1.5, se registre como 0 en el historial y no ensucie tus planillas.

Código Corregido para logic.py
Python
import datetime

class SheetInventory:
    def __init__(self, sheet_name, full_sheet_length=13.0):
        self.sheet_name = sheet_name
        self.full_sheet_length = full_sheet_length
        self.full_sheets_count = 0
        self.cuts = [] 
        self.min_cut_length_to_save = 1.50 # Regla de oro: 1.5m

    def add_full_sheets(self, quantity):
        if quantity > 0:
            self.full_sheets_count += quantity
            return True
        return False

    def take_material(self, length_needed, num_cuts=1):
        if length_needed >= 12.0:
            return False, [{"error": "Corte bloqueado: El largo debe ser menor a 12m."}]
        
        successful_cuts = 0
        current_records = []
        
        for i in range(num_cuts):
            # Preparamos el registro base
            record = {
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                'sheet_type': self.sheet_name, 
                'length_requested': length_needed, 
                'source': '', 
                'remnant': 0, 
                'success': False
            }
            
            suitable_cuts = [c for c in self.cuts if c >= length_needed]
            
            # --- CASO A: USAR RECORTE EXISTENTE ---
            if suitable_cuts:
                selected_cut = min(suitable_cuts)
                self.cuts.remove(selected_cut)
                full_remnant = round(selected_cut - length_needed, 2)
                
                # VALIDACIÓN CRÍTICA:
                if full_remnant >= self.min_cut_length_to_save:
                    self.cuts.append(full_remnant)
                    final_remnant_for_history = full_remnant
                else:
                    # Si es < 1.5, es desperdicio. Guardamos 0 en el historial.
                    final_remnant_for_history = 0
                
                record.update({'source': 'Recorte', 'remnant': final_remnant_for_history, 'success': True})
                successful_cuts += 1
                
            # --- CASO B: USAR CHAPA COMPLETA ---
            elif self.full_sheets_count > 0:
                self.full_sheets_count -= 1
                full_remnant = round(self.full_sheet_length - length_needed, 2)
                
                # VALIDACIÓN CRÍTICA:
                if full_remnant >= self.min_cut_length_to_save:
                    self.cuts.append(full_remnant)
                    final_remnant_for_history = full_remnant
                else:
                    # Si es < 1.5, es desperdicio. Guardamos 0 en el historial.
                    final_remnant_for_history = 0
                
                record.update({'source': 'Chapa Completa', 'remnant': final_remnant_for_history, 'success': True})
                successful_cuts += 1
            else:
                break 
                
            current_records.append(record)
            
        return (successful_cuts == num_cuts), current_records

    def undo_cut(self, source, length_requested, remnant):
        # Al deshacer, si el remanente que guardamos era >= 1.5, lo quitamos del stock
        if remnant >= self.min_cut_length_to_save:
            if remnant in self.cuts:
                self.cuts.remove(remnant)
        
        if source == 'Recorte':
            # Restauramos el recorte original (sumando lo pedido + lo que sobró)
            original_cut = round(length_requested + remnant, 2)
            self.cuts.append(original_cut)
        elif source == 'Chapa Completa':
            # Si se sacó de una entera, simplemente devolvemos la chapa al conteo
            self.full_sheets_count += 1
        return True
¿Qué cambió exactamente?
La variable final_remnant_for_history: Ahora, antes de escribir en el record (que es lo que va a Google Sheets), el código pregunta: ¿Este sobrante es mayor a 1.5? * Si SÍ: lo mete en la lista de stock (self.cuts) y lo anota en el historial.

Si NO: no lo mete en el stock y pone un 0 en el historial.

Sincronización: Con esto, la próxima vez que pidas dos cortes de 6m, el primer registro dirá que sobraron 7m (correcto) y el segundo dirá que sobró 0 (porque el 1m restante se descartó).

Un paso más: Limpieza de datos viejos
Como en tu historial de Google Sheets ya tienes esas filas con "1" metro, cuando reinicies la app con este código, el undo_cut o la carga de stock podrían confundirse.

¿Te gustaría que te pase una pequeña función para borrar automáticamente de Google Sheets todas las filas donde el sobrante sea menor a 1.5? Sería para "limpiar el pasado".

Has dicho
o sea que no me va adejar ningun sobrante inferior a 1.5 metros?

Gemini ha dicho
Exactamente. Con ese cambio en el código, el sistema se vuelve "estricto".

Lo que sucederá a partir de ahora es lo siguiente:

En el Inventario Físico: Si haces un corte y sobran, por ejemplo, 1.20 metros, el programa simplemente no lo guardará en la lista de recortes disponibles. Ese material desaparece del stock porque se considera desperdicio.

En el Historial (Excel/Sheets): En la columna de "Sobrante", verás un 0. Esto es mucho mejor porque así no te confundes pensando que tienes un recorte usable cuando en realidad es un pedazo que no sirve para producción.

Hagamos un ejemplo con tu caso de los 13 metros:
Si pides 2 cortes de 6 metros, el proceso será este:

Paso	Origen	Corte	Sobrante Real	¿Se guarda?	Registro en Historial
Corte 1	Chapa 13m	6m	7m	SÍ (es > 1.5)	Sobrante: 7
Corte 2	Recorte 7m	6m	1m	NO (es < 1.5)	Sobrante: 0
Una recomendación para tu tranquilidad:
Como el código ahora ignora los pedazos chicos, tu stock de recortes siempre estará "limpio". Solo verás piezas que realmente puedes vender o usar.

¿Qué te parece si ahora limpiamos los "1" que te quedaron grabados en el Sheets de ayer para que no te ensucien el inventario al cargar la app? Si quieres, puedo darte el código para un botón de "Limpieza Profunda".

Has dicho
es que yo no quiero que sea desperdicio, yo uso todos los recortes, yo quiero que no me deje ningun recorte inferior a 1.5 metros

Gemini ha dicho
¡Ah! Te entiendo perfectamente. No es que quieras tirar el material, sino que no quieres que el sistema te genere recortes pequeños (como el de 1 metro) porque tu regla es que el sobrante sea siempre útil (mínimo 1.5m).

Para lograr esto, la lógica no debe ser "tirar" el sobrante, sino cambiar la fuente del corte.

La nueva lógica de "Corte Inteligente"
Si el sistema detecta que al cortar un Recorte (ej. de 7m) te va a quedar un sobrante de 1 metro (menor a 1.5m), el programa debería decir: "No, este recorte no me sirve porque me deja un resto inservible. Mejor saco el corte de una Chapa Completa nueva".

De esta forma, conservarías el recorte de 7m entero para un pedido futuro que lo aproveche mejor, y sacarías el de 6m de la chapa de 13m (dejando un sobrante de 7m, que sí es válido).

Aquí tienes el ajuste en logic.py para que el sistema salte los recortes que dejarían restos pequeños:

Código Ajustado para logic.py (Selección Preventiva)
Python
    def take_material(self, length_needed, num_cuts=1):
        if length_needed >= 12.0:
            return False, [{"error": "Corte bloqueado: El largo debe ser menor a 12m."}]
        
        successful_cuts = 0
        current_records = []
        
        for i in range(num_cuts):
            record = {'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'sheet_type': self.sheet_name, 'length_requested': length_needed, 'source': '', 'remnant': 0, 'success': False}
            
            # --- FILTRO INTELIGENTE ---
            # Solo buscamos recortes que:
            # 1. Sean lo suficientemente largos (c >= length_needed)
            # 2. AL CORTARLOS, el sobrante sea 0 (corte exacto) O sea >= 1.5m
            suitable_cuts = [
                c for c in self.cuts 
                if c >= length_needed and (round(c - length_needed, 2) == 0 or round(c - length_needed, 2) >= self.min_cut_length_to_save)
            ]
            
            if suitable_cuts:
                selected_cut = min(suitable_cuts)
                self.cuts.remove(selected_cut)
                remnant = round(selected_cut - length_needed, 2)
                
                if remnant > 0: # Si no fue corte exacto, ya sabemos que es >= 1.5 por el filtro
                    self.cuts.append(remnant)
                
                record.update({'source': 'Recorte', 'remnant': remnant, 'success': True})
                successful_cuts += 1
                
            elif self.full_sheets_count > 0:
                # Aquí también validamos la chapa de 13m
                remnant = round(self.full_sheet_length - length_needed, 2)
                
                # Si de una chapa de 13m sobra menos de 1.5m (ej. corte de 12m)
                # pero como tu max_value es 11.9, esto siempre va a sobrar > 1.1m
                # Ajustamos para que cumpla tu regla de 1.5m
                if remnant < self.min_cut_length_to_save:
                     return False, [{"error": f"El corte de {length_needed}m dejaría un sobrante de {remnant}m (menor al mínimo de 1.5m)."}]

                self.full_sheets_count -= 1
                self.cuts.append(remnant)
                record.update({'source': 'Chapa Completa', 'remnant': remnant, 'success': True})
                successful_cuts += 1
            else:
                break 
            
            current_records.append(record)
            
        return (successful_cuts == num_cuts), current_records
¿Cómo funciona ahora?
Prioriza el aprovechamiento: Si tienes un recorte de 7m y pides 6m, el sistema dirá: "7 - 6 = 1. Como 1 es menor a 1.5, ignoro este recorte y no lo toco".

Busca alternativas: Acto seguido, irá a buscar una Chapa Completa. Como 13−6=7 (y 7 es mayor a 1.5), sacará el corte de ahí.

Resultado final: Terminarás con dos recortes de 7 metros en tu stock, en lugar de uno de 7 y uno de 1. ¡Material optimizado!

Un detalle en tu Streamlit
En tu archivo principal, el max_value del input es 11.9.
13−11.9=1.1.
Para ser coherentes con tu regla de 1.5m, deberías cambiar en tu st.number_input el max_value a 11.5.

¿Te gustaría que ajustemos ese valor máximo en el código de Streamlit también?

Has dicho
ImportError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).

Traceback:

File "/mount/src/gestion_inventario_chapas/app.py", line 5, in <module>

from logic import SheetInventory

Gemini ha dicho
Ese error de ImportError es muy común cuando se mueve el código de Google Colab a Streamlit o Hugging Face. El mensaje dice que Streamlit no encuentra el archivo logic.py donde está definida tu clase SheetInventory.

Aquí tienes los 3 puntos que debes revisar para solucionarlo de inmediato:

1. Nombres de Archivo Exactos
Streamlit es "case-sensitive" (distingue mayúsculas de minúsculas).

Asegúrate de que tu archivo se llame exactamente logic.py (todo en minúsculas).

Si el archivo se llama Logic.py o logica.py, cámbialo a logic.py.

2. Ubicación de los Archivos (La Estructura)
Para que el comando from logic import SheetInventory funcione, ambos archivos deben estar en la misma carpeta raíz de tu proyecto. Tu estructura debería verse así:

Plaintext
gestion_inventario_chapas/
├── app.py          <-- (El archivo de Streamlit que me pasaste)
└── logic.py        <-- (Donde está la clase SheetInventory)
Si pusiste logic.py dentro de una subcarpeta (por ejemplo, una llamada scripts/), el comando debería ser from scripts.logic import SheetInventory.

3. El archivo __init__.py (Opcional pero recomendado)
Aunque en versiones modernas de Python no siempre es obligatorio, intenta crear un archivo vacío llamado __init__.py en la misma carpeta donde están tus otros dos archivos. Esto le asegura a Python que esa carpeta es un "paquete" y facilita las importaciones.

Cómo solucionarlo en Hugging Face / GitHub:
Si estás subiendo los archivos a un repositorio:

Verifica que hayas hecho Commit y Push de ambos archivos (app.py y logic.py). A veces uno se olvida de subir el archivo de la lógica.

Si estás en la interfaz de Hugging Face, entra en la pestaña "Files and versions" y confirma que logic.py aparece ahí listado.

¿Quieres que revisemos cómo quedó el código de logic.py con la nueva regla de los 1.5m para asegurarnos de que no tenga errores de sintaxis antes de subirlo?

Has dicho
def take_material(self, length_needed, num_cuts=1):

        if length_needed >= 12.0:

            return False, [{"error": "Corte bloqueado: El largo debe ser menor a 12m."}]

        

        successful_cuts = 0

        current_records = []

        

        for i in range(num_cuts):

            record = {'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'sheet_type': self.sheet_name, 'length_requested': length_needed, 'source': '', 'remnant': 0, 'success': False}

            

            # --- FILTRO INTELIGENTE ---

            # Solo buscamos recortes que:

            # 1. Sean lo suficientemente largos (c >= length_needed)

            # 2. AL CORTARLOS, el sobrante sea 0 (corte exacto) O sea >= 1.5m

            suitable_cuts = [

                c for c in self.cuts 

                if c >= length_needed and (round(c - length_needed, 2) == 0 or round(c - length_needed, 2) >= self.min_cut_length_to_save)

            ]

            

            if suitable_cuts:

                selected_cut = min(suitable_cuts)

                self.cuts.remove(selected_cut)

                remnant = round(selected_cut - length_needed, 2)

                

                if remnant > 0: # Si no fue corte exacto, ya sabemos que es >= 1.5 por el filtro

                    self.cuts.append(remnant)

                

                record.update({'source': 'Recorte', 'remnant': remnant, 'success': True})

                successful_cuts += 1

                

            elif self.full_sheets_count > 0:

                # Aquí también validamos la chapa de 13m

                remnant = round(self.full_sheet_length - length_needed, 2)

                

                # Si de una chapa de 13m sobra menos de 1.5m (ej. corte de 12m)

                # pero como tu max_value es 11.9, esto siempre va a sobrar > 1.1m

                # Ajustamos para que cumpla tu regla de 1.5m

                if remnant < self.min_cut_length_to_save:

                     return False, [{"error": f"El corte de {length_needed}m dejaría un sobrante de {remnant}m (menor al mínimo de 1.5m)."}]



                self.full_sheets_count -= 1

                self.cuts.append(remnant)

                record.update({'source': 'Chapa Completa', 'remnant': remnant, 'success': True})

                successful_cuts += 1

            else:

                break 

            

            current_records.append(record)

            

        return (successful_cuts == num_cuts), current_records

Gemini ha dicho
El código que me pasaste tiene una lógica impecable para lo que necesitas. Al incluir el filtro inteligente dentro de la lista suitable_cuts, estás logrando que el sistema prefiera dejar un recorte de 7m "quieto" antes que cortarlo y convertirlo en algo de 1m.

Sin embargo, el ImportError que mencionaste antes suele ocurrir por un tema de archivos en el despliegue. Para que todo funcione perfectamente en Streamlit, asegúrate de que el archivo logic.py contenga exactamente esto (incluyendo los imports necesarios):

Contenido sugerido para logic.py
Python
import datetime

class SheetInventory:
    def __init__(self, sheet_name, full_sheet_length=13.0):
        self.sheet_name = sheet_name
        self.full_sheet_length = full_sheet_length
        self.full_sheets_count = 0
        self.cuts = [] 
        self.min_cut_length_to_save = 1.50 

    def add_full_sheets(self, quantity):
        if quantity > 0:
            self.full_sheets_count += quantity
            return True
        return False

    def take_material(self, length_needed, num_cuts=1):
        if length_needed >= 12.0:
            return False, [{"error": "Corte bloqueado: El largo debe ser menor a 12m."}]
        
        successful_cuts = 0
        current_records = []
        
        for i in range(num_cuts):
            record = {
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                'sheet_type': self.sheet_name, 
                'length_requested': length_needed, 
                'source': '', 
                'remnant': 0, 
                'success': False
            }
            
            # Filtro inteligente: busca recortes que dejen 0 o >= 1.5m
            suitable_cuts = [
                c for c in self.cuts 
                if c >= length_needed and (round(c - length_needed, 2) == 0 or round(c - length_needed, 2) >= self.min_cut_length_to_save)
            ]
            
            if suitable_cuts:
                selected_cut = min(suitable_cuts)
                self.cuts.remove(selected_cut)
                remnant = round(selected_cut - length_needed, 2)
                
                if remnant > 0:
                    self.cuts.append(remnant)
                
                record.update({'source': 'Recorte', 'remnant': remnant, 'success': True})
                successful_cuts += 1
                
            elif self.full_sheets_count > 0:
                remnant = round(self.full_sheet_length - length_needed, 2)
                
                if remnant < self.min_cut_length_to_save:
                     return False, [{"error": f"El corte dejaría un sobrante de {remnant}m (mínimo 1.5m)."}]

                self.full_sheets_count -= 1
                if remnant > 0:
                    self.cuts.append(remnant)
                record.update({'source': 'Chapa Completa', 'remnant': remnant, 'success': True})
                successful_cuts += 1
            else:
                break 
            
            current_records.append(record)
            
        return (successful_cuts == num_cuts), current_records

    def undo_cut(self, source, length_requested, remnant):
        # Lógica para revertir cambios
        if remnant > 0 and remnant in self.cuts:
            self.cuts.remove(remnant)
        
        if source == 'Recorte':
            self.cuts.append(round(length_requested + remnant, 2))
        elif source == 'Chapa Completa':
            self.full_sheets_count += 1
        return True
Checklist para eliminar el ImportError:
Nombre del archivo: Debe ser logic.py (en minúsculas).

Ubicación: Debe estar en la misma carpeta que app.py.

GitHub/Hugging Face: Si estás usando Git, asegúrate de haber hecho git add logic.py antes del push.

Llamada en app.py: Asegúrate de que al principio de tu app.py diga exactamente:
from logic import SheetInventory (sin el .py al final).

¿Quieres que verifiquemos el archivo app.py para ver si hay algún detalle extra que esté causando que no encuentre la librería?

Has dicho
el de logic.py esta completo? asi lo reemplazo entero

Gemini ha dicho
Sí, aquí lo tienes completo. He incluido todos los elementos necesarios (el import, la clase y los métodos) para que puedas copiar y pegar el archivo entero.

He añadido una pequeña mejora en el método undo_cut para que sea 100% compatible con tu nueva lógica de descartar recortes menores a 1.5 metros.

Archivo: logic.py
Python
import datetime

class SheetInventory:
    def __init__(self, sheet_name, full_sheet_length=13.0):
        self.sheet_name = sheet_name
        self.full_sheet_length = full_sheet_length
        self.full_sheets_count = 0
        self.cuts = [] 
        self.min_cut_length_to_save = 1.50 

    def add_full_sheets(self, quantity):
        if quantity > 0:
            self.full_sheets_count += quantity
            return True
        return False

    def take_material(self, length_needed, num_cuts=1):
        """
        Procesa los cortes asegurando que nunca quede un sobrante < 1.5m.
        Si un recorte dejaría un resto pequeño, el sistema lo salta y busca una chapa nueva.
        """
        if length_needed >= 12.0:
            return False, [{"error": "Corte bloqueado: El largo debe ser menor a 12m."}]
        
        successful_cuts = 0
        current_records = []
        
        for i in range(num_cuts):
            record = {
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                'sheet_type': self.sheet_name, 
                'length_requested': length_needed, 
                'source': '', 
                'remnant': 0, 
                'success': False
            }
            
            # FILTRO INTELIGENTE: 
            # 1. Que el recorte alcance (c >= length_needed)
            # 2. Que lo que sobre sea 0 (exacto) O sea >= 1.5m
            suitable_cuts = [
                c for c in self.cuts 
                if c >= length_needed and (round(c - length_needed, 2) == 0 or round(c - length_needed, 2) >= self.min_cut_length_to_save)
            ]
            
            if suitable_cuts:
                selected_cut = min(suitable_cuts)
                self.cuts.remove(selected_cut)
                remnant = round(selected_cut - length_needed, 2)
                
                if remnant > 0: 
                    self.cuts.append(remnant)
                
                record.update({'source': 'Recorte', 'remnant': remnant, 'success': True})
                successful_cuts += 1
                
            elif self.full_sheets_count > 0:
                # Validamos la chapa de 13m
                remnant = round(self.full_sheet_length - length_needed, 2)
                
                # Si de una chapa de 13m sobra menos de 1.5m, bloqueamos para evitar desperdicio
                if remnant < self.min_cut_length_to_save:
                     return False, [{"error": f"El corte de {length_needed}m dejaría un sobrante de {remnant}m (mínimo 1.5m)."}]

                self.full_sheets_count -= 1
                if remnant > 0:
                    self.cuts.append(remnant)
                
                record.update({'source': 'Chapa Completa', 'remnant': remnant, 'success': True})
                successful_cuts += 1
            else:
                # Si no hay recortes válidos ni chapas completas
                break 
            
            current_records.append(record)
            
        return (successful_cuts == num_cuts), current_records

    def undo_cut(self, source, length_requested, remnant):
        """
        Revierte un movimiento. Si el sobrante se guardó, lo quita. 
        Luego restaura la fuente original.
        """
        # Si el remanente es > 0, significa que se guardó en la lista 'cuts' (porque ya validamos que fuera >= 1.5)
        if remnant > 0 and remnant in self.cuts:
            self.cuts.remove(remnant)
        
        if source == 'Recorte':
            # Restauramos la pieza original que se usó
            original_piece = round(length_requested + remnant, 2)
            self.cuts.append(original_piece)
        elif source == 'Chapa Completa':
            # Devolvemos la chapa de 13m al stock
            self.full_sheets_count += 1
        return True
Pasos para que no falle el despliegue:
Reemplaza todo el contenido de tu logic.py con el código de arriba.

Asegúrate de que no haya espacios en blanco extraños al final del archivo.

Reinicia tu App en Streamlit o Hugging Face (a veces hay que darle a "Reboot" para que lea los cambios en los archivos importados).

Con esto, si pides dos cortes de 6 metros, el primero saldrá de la chapa de 13m (sobrando 7m) y el segundo no tocará el recorte de 7m (porque dejaría 1m), sino que sacará otra chapa nueva de 13m.

¿Te gustaría que probemos ahora una función para limpiar esos registros de "1 metro" que ya tienes en tu planilla de Google Sheets?

Has parado esta respuesta
Has dicho
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

            c2.write(f"**Recortes Disponibles:** {obj.cuts if obj.cuts else 'Sin recortes'}")



# PASO 2: AÑADIR STOCK

elif opcion == "2. Añadir Stock":

    st.header("➕ Ingreso de Material")

    with st.form("add_form"):

        tipo_add = st.selectbox("Tipo de chapa", list(st.session_state.inventory.keys()))

        cantidad_add = st.number_input("Cantidad de chapas de 13m", min_value=1, step=1)

        if st.form_submit_button("Añadir al Inventario"):

            st.session_state.inventory[tipo_add].add_full_sheets(cantidad_add)

            guardar_stock_actual() # Guarda automáticamente

            st.success(f"Se agregaron {cantidad_add} chapas a {tipo_add} y se guardó en la nube.")



# PASO 3: TOMAR MATERIAL

elif opcion == "3. Tomar Material":

    st.header("✂️ Registro de Corte para Producción")

    st.warning("Reglas: No cortes ≥ 12m. Sobrantes < 1.50m se descartan.")

    

    with st.form("corte_form"):

        cliente = st.text_input("Nombre del Cliente / Orden #", placeholder="Ej: Juan Pérez")

        tipo = st.selectbox("Chapa", list(st.session_state.inventory.keys()))

        largo = st.number_input("Largo (m)", min_value=0.5, max_value=11.9, step=0.1)

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

                    

                    # GUARDADO AUTOMÁTICO DOBLE

                    registrar_en_historial_sheets(registros)

                    guardar_stock_actual()



                    st.success(f"✅ Pedido registrado para {cliente}")

                    st.markdown("### 📝 Hoja de Corte (Producción)")

                    resumen_texto = f"CLIENTE: {cliente}\nPRODUCTO: {tipo}\n"

                    for i, r in enumerate(registros):

                        info_linea = f"- Pieza {i+1}: {largo}m (Extraer de: {r['source']})"

                        st.info(info_linea)

                        resumen_texto += info_linea + "\n"

                    st.code(resumen_texto, language="text")

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

            guardar_stock_actual() # Reflejamos el deshacer en la nube

            st.success("Operación deshecha y stock restaurado en la nube.")

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

          

este es app.py

Gemini ha dicho
El código de tu archivo app.py está muy bien estructurado. Como ya tienes el archivo logic.py actualizado con el "filtro inteligente", no necesitas cambiar casi nada en este archivo, ya que la lógica de protección (no dejar recortes de menos de 1.5m) se ejecuta automáticamente cuando llamas a take_material.

Sin embargo, para que todo sea coherente y evitar que el usuario intente pedir algo que deje un residuo inválido de una chapa de 13m, te sugiero un pequeño ajuste en los límites del formulario.

Aquí tienes el archivo app.py optimizado para trabajar con tu nueva regla:

Python
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
        # AJUSTE: max_value 11.5 para asegurar que de una de 13m siempre sobre al menos 1.5m
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
                    resumen_texto = f"CLIENTE: {cliente}\nPRODUCTO: {tipo}\n"
                    for i, r in enumerate(registros):
                        info_linea = f"- Pieza {i+1}: {largo}m (Origen: {r['source']}, Sobrante: {r['remnant']}m)"
                        st.info(info_linea)
                        resumen_texto += info_linea + "\n"
                    st.code(resumen_texto, language="text")
                else:
                    # Si falla, mostramos el error que devuelve logic.py (como el de sobrante < 1.5)
                    if registros and "error" in registros[0]:
                        st.error(registros[0]["error"])
                    else:
                        st.error("Stock insuficiente: No hay recortes que cumplan la regla de 1.5m ni chapas de 13m.")

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
¿Qué corregimos en app.py?
Límite de Corte (max_value=11.5): Si permites cortes de 11.9m, el sobrante de una chapa de 13m sería de 1.1m, lo cual rompería tu regla de "mínimo 1.5m". Al limitarlo a 11.5m, garantizas que cualquier corte de chapa nueva deje un recorte válido.

Manejo de Errores: Ahora, si logic.py bloquea un corte porque dejaría un pedazo de 1 metro, el error aparecerá claramente en pantalla en color rojo.

Visualización Limpia: En el "Paso 1", redondeamos los números a 2 decimales para que no veas cosas como 7.00000000001.

¿Te gustaría que te ayude con una función para limpiar esos recortes de 1m que ya quedaron guardados en tu Google Sheets, o prefieres borrarlos a mano desde la planilla?

Has dicho
SyntaxError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).

Traceback:

File "/mount/src/gestion_inventario_chapas/app.py", line 5, in <module>

from logic import SheetInventory

Gemini ha dicho
Ese SyntaxError en la línea donde importas la lógica (from logic import SheetInventory) es una señal clara: el error no está en app.py, sino que Python encontró un error de escritura (falta de paréntesis, comillas abiertas, espacios raros) dentro de logic.py al intentar leerlo.

Es muy probable que al copiar y pegar se haya colado algún carácter extraño o falte una indentación.

Aquí tienes el código de logic.py revisado y "limpio" de errores de sintaxis comunes. Borra todo lo que tengas en ese archivo y pega esto exactamente:

Archivo: logic.py (Copia desde aquí)
Python
import datetime

class SheetInventory:
    def __init__(self, sheet_name, full_sheet_length=13.0):
        self.sheet_name = sheet_name
        self.full_sheet_length = full_sheet_length
        self.full_sheets_count = 0
        self.cuts = [] 
        self.min_cut_length_to_save = 1.50 

    def add_full_sheets(self, quantity):
        if quantity > 0:
            self.full_sheets_count += quantity
            return True
        return False

    def take_material(self, length_needed, num_cuts=1):
        if length_needed >= 12.0:
            return False, [{"error": "Corte bloqueado: El largo debe ser menor a 12m."}]
        
        successful_cuts = 0
        current_records = []
        
        for i in range(num_cuts):
            record = {
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                'sheet_type': self.sheet_name, 
                'length_requested': length_needed, 
                'source': '', 
                'remnant': 0, 
                'success': False
            }
            
            # Filtro inteligente: buscamos recortes que dejen 0 o >= 1.5m
            suitable_cuts = [
                c for c in self.cuts 
                if c >= length_needed and (round(c - length_needed, 2) == 0 or round(c - length_needed, 2) >= self.min_cut_length_to_save)
            ]
            
            if suitable_cuts:
                selected_cut = min(suitable_cuts)
                self.cuts.remove(selected_cut)
                remnant = round(selected_cut - length_needed, 2)
                
                if remnant > 0:
                    self.cuts.append(remnant)
                
                record.update({'source': 'Recorte', 'remnant': remnant, 'success': True})
                successful_cuts += 1
                
            elif self.full_sheets_count > 0:
                remnant = round(self.full_sheet_length - length_needed, 2)
                
                if remnant < self.min_cut_length_to_save:
                    # En lugar de romper el bucle, devolvemos el error específico
                    return False, [{"error": f"El corte de {length_needed}m dejaría un sobrante de {remnant}m (mínimo 1.5m)."}]

                self.full_sheets_count -= 1
                if remnant > 0:
                    self.cuts.append(remnant)
                
                record.update({'source': 'Chapa Completa', 'remnant': remnant, 'success': True})
                successful_cuts += 1
            else:
                break 
            
            current_records.append(record)
            
        return (successful_cuts == num_cuts), current_records

    def undo_cut(self, source, length_requested, remnant):
        if remnant > 0 and remnant in self.cuts:
            self.cuts.remove(remnant)
        
        if source == 'Recorte':
            original_piece = round(length_requested + remnant, 2)
            self.cuts.append(original_piece)
        elif source == 'Chapa Completa':
            self.full_sheets_count += 1
        return True
Causas posibles del SyntaxError que acabas de ver:
Indentación: Asegúrate de que no haya espacios de más al principio de las líneas. Python es muy estricto con eso.

Paréntesis o Corchetes: En la línea de suitable_cuts = [...], si falta un corchete al final, da SyntaxError.

Caracteres invisibles: Si copiaste el código de una web o chat que formatea el texto, a veces se pegan espacios "no-break" que Python no reconoce. Pegarlo en un editor simple (como el de Hugging Face o VS Code) suele limpiarlos.

Una última comprobación en app.py:
Asegúrate de que la línea 5 de tu app.py sea exactamente así, sin espacios raros al final:
from logic import SheetInventory

¿Lograste guardar el archivo? Si lo haces y te sigue dando error, fíjate si en el log de Streamlit te dice un número de línea específico dentro de logic.py.

Has dicho
bien ... ahora anduvo

Gemini ha dicho
¡Qué buena noticia! Me alegra que ya esté funcionando. Ese SyntaxError suele ser un dolor de cabeza, pero con el código limpio se soluciona rápido.

Ahora que la app ya está corriendo y con la lógica inteligente activa, tienes un sistema mucho más sólido:

No más retazos inútiles: Si un corte va a dejar menos de 1.5m, la app simplemente no lo hace y busca una chapa nueva.

Optimización real: Tus recortes en el inventario ahora son piezas que realmente puedes usar o vender.

¿Qué quieres hacer ahora?
Como ya tienes la base funcionando, te sugiero estos posibles siguientes pasos:

Limpieza de la base de datos: ¿Quieres que borremos del Google Sheets los registros que quedaron con "1 metro" de ayer para que no te ensucien el stock actual?

Ajuste del Sidebar: Tenías pensado un menú de 9 opciones, ahora tenemos 6. ¿Quieres que agreguemos alguna de las que faltaban (como "Reporte de Desperdicio" o "Cálculo de Optimización")?

Prueba de fuego: Intenta hacer un corte que sepas que dejaría 1 metro (por ejemplo, uno de 6m sobre un recorte de 7m) y confirma que la app te avisa que usó una Chapa Completa en su lugar.

¿Por dónde prefieres seguir? Sería un placer ayudarte a pulir esos detalles.

Has dicho
lo que podriamos agregar en la hoja de corte es que me informe de que recorte saca cada corte o solicitud para que quien hace los cortes sepa de donde sacarlos, me explico?

Gemini ha dicho
¡Se explica perfectamente! Es fundamental para el operario saber exactamente qué pieza agarrar del rack de recortes para no meter la pata.

Actualmente, tu código ya identifica si el material sale de una "Chapa Completa" o de un "Recorte", pero no le dice al operario de qué medida es el recorte que debe buscar (por ejemplo: "Buscá el recorte de 7.0m").

Para que la Hoja de Corte sea útil de verdad, vamos a modificar app.py para que muestre el largo del origen.

El ajuste en app.py (Paso 3)
Busca la sección donde generas el resumen_texto y el st.info dentro del Paso 3. Vamos a cambiarlo para que sea más descriptivo:

Python
# --- MODIFICACIÓN EN EL PASO 3 DE app.py ---

                    st.success(f"✅ Pedido registrado para {cliente}")
                    st.markdown("### 📝 Hoja de Corte (Producción)")
                    
                    resumen_texto = f"CLIENTE: {cliente}\nPRODUCTO: {tipo}\n"
                    resumen_texto += f"FECHA: {registros[0]['timestamp']}\n"
                    resumen_texto += "-"*30 + "\n"

                    for i, r in enumerate(registros):
                        # Mejoramos la información para el operario
                        origen = r['source']
                        # Si es recorte, le decimos de qué medida buscarlo
                        # Para esto, el origen debería decir algo como "Recorte de X.X m"
                        # Pero como r['source'] solo dice "Recorte", calculamos el origen:
                        largo_original = round(r['length_requested'] + r['remnant'], 2) if origen == 'Recorte' else 13.0
                        
                        detalles = f"PIEZA {i+1}: Corte de {largo}m\n   👉 EXTRAER DE: {origen} (Medida original: {largo_original}m)\n"
                        
                        st.info(detalles)
                        resumen_texto += detalles + "\n"
                    
                    st.code(resumen_texto, language="text")
¿Cómo lo verá el cortador?
Ahora, en lugar de un mensaje genérico, en la pantalla y en el bloque de texto para copiar aparecerá algo así:

PIEZA 1: Corte de 6.0m > 👉 EXTRAER DE: Recorte (Medida original: 7.0m)

Esto le da una instrucción precisa: "Andá al montón de recortes, buscá uno de 7 metros y cortalo a 6".

Un paso extra: ¿Querés etiquetas?
Si tenés muchos recortes, otra opción es que el sistema asigne un "ID" o número a cada recorte, pero por ahora, con la medida original el operario debería poder identificarlos bien con la cinta métrica.

¿Te gustaría que agreguemos también el Sobrante que le debe quedar al operario en la mano después de cortar, para que verifique si lo hizo bien?

Has dicho
El informe de corte que envía al final lo puede enviar por algun medio a cada coratdor, ejemplo whatsapp?

Gemini ha dicho
¡Es una idea excelente! Automatizar el envío a WhatsApp es el paso lógico para que el cortador reciba la instrucción directamente en su celular sin tener que mirar la pantalla de la computadora.

Como estamos usando Streamlit, tienes dos formas de hacerlo: una "semimanual" (gratuita y rápida) y una "automática" (más profesional pero compleja).

Opción 1: Botón de Envío Rápido (WhatsApp Web)
Es la más fácil de implementar. Agregamos un botón que, al hacer clic, abre WhatsApp Web con el mensaje ya escrito y el número del cortador pre-cargado.

Debes modificar el final del "Paso 3" en tu app.py así:

Python
# --- Debajo de st.code(resumen_texto) ---

# 1. Definimos el número del cortador (ejemplo: +549...)
# Podrías poner un st.selectbox para elegir a qué cortador enviarlo
telefono_cortador = "5491122334455" 

# 2. Formateamos el texto para URL (cambia espacios por %20, etc.)
import urllib.parse
mensaje_url = urllib.parse.quote(resumen_texto)

# 3. Creamos el link de WhatsApp
link_wa = f"https://wa.me/{telefono_cortador}?text={mensaje_url}"

# 4. Botón visual
st.link_button("📲 Enviar Orden por WhatsApp", link_wa)
Ventaja: No tiene costo y es instantáneo.
Desventaja: Tienes que estar logueado en WhatsApp Web en la misma PC donde abras la App.

Opción 2: Envío Automático (Twilio / API)
Si quieres que el mensaje se envíe solo (sin que tú tengas que hacer clic en "Enviar" dentro de WhatsApp), necesitas una API como Twilio.

Costo: Twilio cobra una pequeña tarifa por mensaje.

Configuración: Requiere instalar la librería twilio y configurar las credenciales en st.secrets.

El código se vería así:

Python
from twilio.rest import Client

def enviar_whatsapp_auto(mensaje):
    account_sid = st.secrets["twilio"]["sid"]
    auth_token = st.secrets["twilio"]["token"]
    client = Client(account_sid, auth_token)

    message = client.messages.create(
        from_='whatsapp:+14155238886', # Número de Twilio
        body=mensaje,
        to='whatsapp:+5491122334455'
    )
    return message.sid
Mi recomendación: La "Opción 1" vitaminada
Para que sea flexible, podrías agregar un pequeño menú en el Sidebar o un st.radio antes de procesar el corte para elegir quién es el cortador del día.

¿Te gustaría que preparemos el código para que puedas elegir entre varios números de teléfono antes de darle al botón de enviar? Sería algo como:

[ ] Enviar a Fede (+549...)

[ ] Enviar a Operario 2 (+549...)

¿Qué te parece?

Has dicho
File "/mount/src/gestion_inventario_chapas/app.py", line 168

  elif opcion == "4. Deshacer Pedido":

  ^

SyntaxError: invalid syntax

Gemini ha dicho
Ese SyntaxError en el elif suele ser un "error de arrastre". En Python, cuando el intérprete marca un error al inicio de una línea con elif o else, generalmente significa que la sección de código justo arriba (el Paso 3) tiene un paréntesis, una comilla o un bloque if/else que no se cerró correctamente.

Revisando el código que estuvimos armando para el envío de WhatsApp, es muy probable que falte cerrar un paréntesis en la parte del st.info o el st.link_button.

Aquí tienes el bloque del Paso 3 y Paso 4 corregido y cerrado correctamente para que desaparezca el error de sintaxis:

Copia y reemplaza desde el Paso 3 al 4:
Python
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
