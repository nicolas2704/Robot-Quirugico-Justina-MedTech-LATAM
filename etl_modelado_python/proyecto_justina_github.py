# Librerias
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pyodbc # Necesario para que SQLAlchemy pueda usarlo internamente
from sqlalchemy import create_engine
from pathlib import Path # No se usa en este script
import google.generativeai as genai
import os
import json
import time
import glob
import random
import re
import io
from dotenv import load_dotenv
load_dotenv()


# variables
paises_excel="/home/nicolas27/data/proyecto_grupal_no_country/fuentes_serias/fuentes_definitivas/paises_tabla.xlsx"
archivo_registro="/home/nicolas27/data/proyecto_grupal_no_country/fuentes_serias/fuentes_definitivas/codigo_de_registro_justina.txt"
hospitales_pub_excel="/home/nicolas27/data/proyecto_grupal_no_country/fuentes_serias/fuentes_definitivas/hospitales_publicos_robots.xlsx"
hospìtales_pri_excel="/home/nicolas27/data/proyecto_grupal_no_country/fuentes_serias/fuentes_definitivas/hospitales_privados_robots.xlsx"
archivo_rankings_hosp="/home/nicolas27/data/proyecto_grupal_no_country/fuentes_serias/fuentes_definitivas/Ranking-Calidad-2025.pdf"
competidores_excel="/home/nicolas27/data/proyecto_grupal_no_country/fuentes_serias/fuentes_definitivas/competidores_tabla.xlsx"
tabla_hospitales="/home/nicolas27/data/proyecto_grupal_no_country/fuentes_serias/fuentes_definitivas/hospitales_completos.xlsx"
tabla_intermedia="/home/nicolas27/data/proyecto_grupal_no_country/fuentes_serias/fuentes_definitivas/hospitales_robotica.xlsx"
tabla_cotizaciones="/home/nicolas27/data/proyecto_grupal_no_country/fuentes_serias/fuentes_definitivas/cotizaciones.xlsx"

# API para utilizar GEMINI
API_KEY= os.getenv("api_key")
genai.configure(api_key=API_KEY)

# REGISTRO
def proceso_log(mensaje):
    formato_tiempo="%Y-%h-%d-%H:%M:%S"
    fecha_actual=datetime.now()
    marca_de_tiempo=fecha_actual.strftime(formato_tiempo)

    with open(archivo_registro, "a") as registro:
        registro.write(marca_de_tiempo + " : "+mensaje+"\n")

# EXTRAER
def extraer():
    # Lista dataframes
    lista_df_extraidos=[]

    try:
        # APIs valores USD
        dolar_latam = requests.get("https://open.er-api.com/v6/latest/USD")
        dolar_arg = requests.get("https://dolarapi.com/v1/dolares")

        # convertir api a formato JSON extraible
        dolar_latam.raise_for_status()
        monedas_latam = dolar_latam.json()
    except Exception as e:
        proceso_log(f"Error en la extracción de APIs: {e}")

    try:
        # extraccion de datos para la tabla paises
        paises_latam = pd.read_excel(paises_excel)

        # carga de las tablas hospitales
        dataframe_hosp_pub = pd.read_excel(hospitales_pub_excel)
        dataframe_hosp_priv = pd.read_excel(hospìtales_pri_excel)

        # carga de la tabla competidores
        dataframe_competidores = pd.read_excel(competidores_excel)
    except Exception as e:
        proceso_log(f"Error en la lectura de archivos Excel: {e}")

    # añadir elementos a la lista de dataframes
    lista_df_extraidos.append(dolar_arg)
    lista_df_extraidos.append(monedas_latam)
    lista_df_extraidos.append(paises_latam)
    lista_df_extraidos.append(dataframe_hosp_pub)
    lista_df_extraidos.append(dataframe_hosp_priv)
    lista_df_extraidos.append(dataframe_competidores)
    
    return lista_df_extraidos
    
# TRANSFORMAR
def transformar(dataframes_extraidos):
    # fecha de hoy
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")

    # fragmentar lista en elementos para la transformacion
    dolar_arg=dataframes_extraidos[0]
    monedas_latam=dataframes_extraidos[1]
    dataframe_paises_latam=dataframes_extraidos[2]
    dataframe_hosp_pub=dataframes_extraidos[3]
    dataframe_hosp_priv=dataframes_extraidos[4]
    dataframe_competidores=dataframes_extraidos[5]

    # Creacion de las monedas y sus valores:
    # DATAFRAME COTIZACIONES

    # dolares de Arg
    monedas_argentinas = dolar_arg.json()
    for item in monedas_argentinas:
        if item["casa"] =="bolsa":
            venta_dolar_mep = item["venta"]
            break

    # diccionario de paises de LATAM
    dic={"ARS":venta_dolar_mep,
         "BOB":monedas_latam["rates"]["BOB"],
         "BRL":monedas_latam["rates"]["BRL"],
         "CLP":monedas_latam["rates"]["CLP"],
         "COP":monedas_latam["rates"]["COP"],
         "CRC":monedas_latam["rates"]["CRC"],
         "CUP":monedas_latam["rates"]["CUP"],
         "USD":monedas_latam["rates"]["USD"],
         "GTQ":monedas_latam["rates"]["GTQ"],
         "HTG":monedas_latam["rates"]["HTG"],
         "HNL":monedas_latam["rates"]["HNL"],
         "MXN":monedas_latam["rates"]["MXN"],
         "NIO":monedas_latam["rates"]["NIO"],
         "PAB":monedas_latam["rates"]["PAB"],
         "PYG":monedas_latam["rates"]["PYG"],
         "PEN":monedas_latam["rates"]["PEN"],
         "DOP":monedas_latam["rates"]["DOP"],
         "UYU":monedas_latam["rates"]["UYU"],
         "VES":monedas_latam["rates"]["VES"],
         "EUR":monedas_latam["rates"]["EUR"]
    }
    
    # convertir y tranformar el diccionario en un dataframe
    dataframe_monedas = pd.json_normalize(dic)
    dataframe_monedas = dataframe_monedas.T
    dataframe_monedas = dataframe_monedas.reset_index() # resetea el indice a partir de 0 y le añade una columna index
    dataframe_monedas.columns = ["id_moneda", "valor"] # fija el nombre de las columnas
    # cambiar tipo de datos y redondeo de valores
    dataframe_monedas["valor"]=dataframe_monedas["valor"].astype(float)
    dataframe_monedas["valor"]=np.round(dataframe_monedas["valor"],2)
    dataframe_monedas["fecha"]=fecha_hoy
    dataframe_monedas["fecha"]=pd.to_datetime(dataframe_monedas["fecha"])
    dataframe_monedas["fecha"] = dataframe_monedas["fecha"].dt.date
    # mostrar dataframe cotizaciones de monedas
    #print(dataframe_monedas)
    # exportar dataframe_monedas
    dataframe_monedas.to_excel(tabla_cotizaciones, index=False)
    #print(dataframe_monedas.dtypes)
    
    # DATAFRAME PAISES
    
    # cambiar el tipo de datos
    dataframe_paises_latam["cantidad_hospitales"]=dataframe_paises_latam["cantidad_hospitales"].astype("Int64")
    dataframe_paises_latam["hosp_publicos"] = pd.to_numeric(dataframe_paises_latam["hosp_publicos"], errors='coerce')
    dataframe_paises_latam["hosp_publicos"]=dataframe_paises_latam["hosp_publicos"].astype("Int64")
    dataframe_paises_latam["hosp_privados"]=dataframe_paises_latam["hosp_privados"].astype("Int64")
    dataframe_paises_latam["cant_quirofanos"]=dataframe_paises_latam["cant_quirofanos"].astype("Int64")
    dataframe_paises_latam["camas_hospitalarias"]=dataframe_paises_latam["camas_hospitalarias"].astype("Int64")
    dataframe_paises_latam["cant_pac_renales_anuales"]=dataframe_paises_latam["cant_pac_renales_anuales"].astype("Int64")
    dataframe_paises_latam["transplantes_anuales"]=dataframe_paises_latam["transplantes_anuales"].astype("Int64")
    dataframe_paises_latam["transplantes_riñon_anuales"]=dataframe_paises_latam["transplantes_riñon_anuales"].astype("Int64")
    # mostrar tabla paises y su tipo de dato
    #print(dataframe_paises_latam)
    #print(dataframe_paises_latam.dtypes)

    # DATAFRAME HOSPITALES

    # PROMPT de uso temporal. Fue utilizado para una generacion de hospitales privados como base
    #ruta_csv_temporal_hosp_priv ="hospitales_priv_csv.csv"
    #dataframe_hosp_pub.to_csv(ruta_csv_temporal_hosp_priv, index=False, sep=",")
    #archivo_subido = genai.upload_file(path=ruta_csv_temporal, mime_type="text/csv")
    prompt_hosp_priv="""ROL: Experto en Data Entry y Análisis de Sistemas de Salud en Latinoamérica.

        CONTEXTO: Poseo una base de datos de salud y requiero identificar exclusivamente clínicas y hospitales PRIVADOS que operen con tecnología de cirugía robótica (Da Vinci, Versius, Hugo RAS, ROSA, Mako SmartRobotics, o Toumai).

        TAREA: Genera un listado detallado para los siguientes países: [Argentina, Bolivia, Brasil,

        Chile, Colombia, Costa Rica, Cuba, Ecuador, El Salvador, Guatemala, Haiti, Honduras, Mexico, Nicaragua, Panamá,Paraguay, Peru, Republica Dominicana, Uruguay y Venezuela]. 

        REQUISITOS TÉCNICOS:
        1. Formato: CSV estricto (bloque de código).
        2. Estructura de Columnas:
        - nombre_hospital: Nombre comercial exacto.
        - tipo_gestion: "Privado".
        - ciudad: Localidad donde reside el equipo.
        - id_pais: ISO Alpha-2.
        - latitud: Coordenada decimal.
        - longitud: Coordenada decimal.
        - robot: Marca/Modelo del robot (si un hospital tiene varios, crear una fila por cada modelo).

        RESTRICCIONES CRÍTICAS:
        - FILTRO DE SEGURIDAD: Solo incluye registros donde exista confirmación pública del uso de estas tecnologías. Si no hay evidencia, omite el hospital.
        - INTEGRIDAD: No inventes coordenadas; si no las conoces, usa la coordenada central de la ciudad.
        - SIN TEXTO: No añadas introducciones ni conclusiones. Solo el bloque de código CSV.

        ORDEN DE PROCESAMIENTO: Empieza por los países con mayor adopción (Brasil, México, Argentina, Colombia, Chile) y continúa con el resto de la lista.
    """

    # sacar columna de fuentes a dataframe de hosp privados
    dataframe_hosp_priv.pop("fuente_verificacion")
    # cambiar tipo de dato de longitud y latitud
    dataframe_hosp_priv["latitud"]=dataframe_hosp_priv["latitud"].astype(str)
    dataframe_hosp_priv["longitud"]=dataframe_hosp_priv["longitud"].astype(str)
    #print(dataframe_hosp_priv)

    # modificar columnas del dataframe hosp pub
    dataframe_hosp_pub["latitud"]=dataframe_hosp_pub["latitud"].astype(str)
    dataframe_hosp_pub["longitud"]=dataframe_hosp_pub["longitud"].astype(str)
    #print(dataframe_hosp_pub)

    # unir tablas de hospitales publicos y privados
    dataframe_hospitales = pd.concat([dataframe_hosp_pub, dataframe_hosp_priv], ignore_index=True)

    # CREACION DE TABLA INTERMEDIA (Hospitales y Competencias)
    # limpiamos las columnas nombre_hospital y robot de mayusculas/minusculas y datos sucios
    dataframe_hospitales["nombre_hospital"]=dataframe_hospitales["nombre_hospital"].str.strip().str.lower()
    dataframe_hospitales["robot"]=dataframe_hospitales["robot"].str.strip().str.lower()

    # Generamos el id_hospital. Con la funcion factorize() tiene en cuenta valores repedidos y unicos
    dataframe_hospitales["id_hospitales"] = pd.factorize(dataframe_hospitales["nombre_hospital"])[0] + 1
    # Generamos el id_competidor. Se realiza un mapeo o busqueda de los robots, para asignarle un valor
    # diccionario de mapeo
    mapeo_fijo ={
        "da vinci": 1,
        "versius": 2,
        "hugo ras": 3,
        "rosa": 4,
        "mako smartrobotics": 5,
        "toumai": 6
    }

    # funcion para asignarle numero
    def asignar_id_robot(nombre_robot):
        # Si el robot está en nuestra lista fija, devolvemos su número
        if nombre_robot in mapeo_fijo:
            return mapeo_fijo[nombre_robot]
        else:
            # Si NO está, le asignamos un número nuevo (dinámico)
            # Esto lo haremos en un paso posterior para mayor precisión
            return None
        
    # llamamos a la funcion
    dataframe_hospitales["id_competidores"]=dataframe_hospitales["robot"].apply(asignar_id_robot)
    # asignar id dinamicos del 7 en adelante para los nuevos robots
    # Identificamos los robots que quedaron sin ID (los que no estaban en la lista fija)
    robots_nuevos = dataframe_hospitales[dataframe_hospitales["id_competidores"].isna()]["robot"].unique()

    # asignar números empezando desde el 7 en adelante
    for i, nombre in enumerate(robots_nuevos):
        dataframe_hospitales.loc[dataframe_hospitales["robot"] == nombre, "id_competidores"] = i + 7

    # Convertir a entero para que no tenga decimales (.0)
    dataframe_hospitales["id_competidores"] = dataframe_hospitales["id_competidores"].astype(int)

    # Crear el nuevo dataframe solo con las 2 columnas que necesitas
    df_inventario_robotico = dataframe_hospitales[["id_hospitales", "id_competidores"]]
    # mostrar tabla intermedia y su tipo de dato
    print(df_inventario_robotico)
    #print(df_inventario_robotico.dtypes)
    # exportar archivos para ver
    df_inventario_robotico.to_excel(tabla_intermedia, index=False)

    # eliminar columnas innecesarias de la tabla hospital
    dataframe_hospitales.pop("robot")
    dataframe_hospitales.pop("id_hospitales")
    dataframe_hospitales.pop("id_competidores")

    # eliminar registros repetidos del dataframe hospitales
    dataframe_hospitales = dataframe_hospitales.drop_duplicates(subset=["nombre_hospital"])

    # AÑADIR COLUMNA RANKING
    ruta_csv_temporal ="hospitales_csv.csv"
    dataframe_hospitales.to_csv(ruta_csv_temporal, index=False, sep=",")
    #archivo_subido = genai.upload_file(path=ruta_csv_temporal, mime_type="text/csv")
    archivo_subido = genai.upload_file(archivo_rankings_hosp, mime_type="application/pdf")

    # darle el nombre de los hospitales y paises al ML
    lista_para_ia = dataframe_hospitales.apply(lambda x: f"- {x["nombre_hospital"]} ({x["id_pais"]})", axis=1).tolist()
    prompt = f"""
        Actúa como un experto en extracción de datos.
        Analiza las tablas "RANKING DIMENSIÓN TECNOLOGÍA" y "RANKING DIMENSIÓN PRESTIGIO" en el PDF.

        Instrucción:
        Compara mi lista de hospitales con los nombres en la columna 'Hospital' de ambas tablas del PDF. 
        Verifica el País para asegurar que es el hospital correcto.

        Lista de hospitales a verificar:
        {chr(10).join(lista_para_ia)}

        Restricciones de Formato (ESTRICTO):
        - Salida: CSV puro, sin bloques de código, sin texto extra.
        - Separador: ";"
        - Encabezados: nom_hosp;ranking
        - En 'nom_hosp': Escribe el nombre EXACTO tal cual aparece en mi lista de arriba.
        - En 'ranking': Escribe 'Si' si aparece en alguna tabla, o 'No' si no aparece.

        IMPORTANTE: No omitas ningún hospital de la lista. Si el nombre es parecido pero el país coincide, márcalo como 'Si'.
    """

    # Usamos modelo 2.5 Flash para que sea rápido y eficiente en costos
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content([archivo_subido, prompt])

    # EXTRAER Y CONVERTIR (Lo que sigue en tu script)
    csv_puro = response.text.replace("```csv", "").replace("```", "").strip()
    df_rankings = pd.read_csv(io.StringIO(csv_puro), sep=";")
    # resetar indices antes de la union
    dataframe_hospitales=dataframe_hospitales.reset_index(drop=True)
    df_rankings=df_rankings.reset_index(drop=True)
    # unir dataframe hospitales y dataframe rankings
    dataframe_hospitales=pd.concat([dataframe_hospitales,df_rankings], axis=1)
    # borrar columna
    dataframe_hospitales.pop("nom_hosp")

    # cambiar la columna pais de la tabla hospitales por las iniciales del pais
    dict_paises = dict(zip(dataframe_paises_latam["nombre_pais"], dataframe_paises_latam["id_pais"]))
    dataframe_hospitales["id_pais"] = dataframe_hospitales["id_pais"].map(dict_paises)

    # exportar tabla hospitales
    dataframe_hospitales.to_excel(tabla_hospitales, index=False)
    print(dataframe_hospitales)
    #print(dataframe_hospitales.dtypes)

    # TABLA COMPETIDORES
    # cambiar tipo de datos
    dataframe_competidores["num_procedimientos_anuales"]=dataframe_competidores["num_procedimientos_anuales"].astype("Int64")
    #print(dataframe_competidores)
    #print(dataframe_competidores.dtypes)

    # cargar dataframes para exportar de la funcion
    lista_df_transformados=[]
    lista_df_transformados.append(dataframe_monedas)
    lista_df_transformados.append(dataframe_paises_latam)
    lista_df_transformados.append(dataframe_hospitales)
    lista_df_transformados.append(dataframe_competidores)
    lista_df_transformados.append(df_inventario_robotico)

    return lista_df_transformados


# carga a base de datos
def cargar_base_de_datos(dataframes_transformados):
    # variables de SQL Server
    nombre_db="proyecto_justina"

    # autenticacion de la BD
    host_servidor_ip=os.getenv("servidor")
    usuario = os.getenv("usuario") # Tu usuario de SQL Server
    contraseña = os.getenv("contraseña") # Tu contraseña real, incluyendo las llaves si son parte de ella
    nombre_tablas = ["cotizaciones", "paises", "hospitales", "competidores_tec", "hospitales_robotica"]
    
    # Validar que coincidan las cantidades
    if len(dataframes_transformados) != len(nombre_tablas):
        print("Error: La cantidad de DataFrames no coincide con la cantidad de tablas.")
        return

    try:
        # Construcción corregida de la cadena de conexión
        connection_string = (
            f"mssql+pyodbc://{usuario}:{contraseña}@{host_servidor_ip}/{nombre_db}?"
            f"driver=ODBC+Driver+18+for+SQL+Server&"
            f"Encrypt=no&"
            f"TrustServerCertificate=yes"
        )
        # Agregamos fast_executemany=True para mayor velocidad
        engine = create_engine(connection_string, fast_executemany=True)
        proceso_log("Conexion de Base de datos de manera exitosa")
        
        print(f"Conectando a {host_servidor_ip}... Iniciando carga de {len(nombre_tablas)} tablas.")
        proceso_log("Realizando Carga de las tablas en la Base de datos")
        # Iterar sobre AMBAS listas al mismo tiempo usando zip
        for dataframe, tabla in zip(dataframes_transformados, nombre_tablas):
            print(f"Cargando datos en la tabla: {tabla}...")
            dataframe.to_sql(tabla, con=engine, if_exists="append", index=False)
        
        print("Todos los datos se cargaron correctamente.")
        proceso_log("Tablas cargadas correctamente en la Base de Datos")
        
    except Exception as ex:
        print(f"Error crítico durante la carga: {ex}")
        proceso_log(f"Ocurrio el error {ex} durante la carga en la Base de Datos")


#extraccion
proceso_log("Proceso de Extraccion Inicializado")
dataframes_extraidos=extraer()
print("datos extraidos")
proceso_log("Proceso de Extraccion Finalizado\n")

#transformacion
proceso_log("Proceso de Transformacion Inicializado")
print("Datos Transformados:")
dataframes_transformados=transformar(dataframes_extraidos)
proceso_log("Proceso de Transformacion Finalizado\n")

#carga
print("datos cargados")
proceso_log("Procesos de Cargas Inicializados")
cargar_base_de_datos(dataframes_transformados)
proceso_log("Procesos de Cargas Finalizados")
proceso_log("Proceso ETL Finalizado\n")