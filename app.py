from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from docx import Document
import mysql.connector
import json
import pika
import subprocess

# Ruta para guardar el archivo Word y el PDF
INPUT_WORD_PATH = '/app/templates/contrato.docx'
OUTPUT_WORD_PATH = '/app/output/contrato_generado.docx'
OUTPUT_PDF_PATH = '/app/output/contrato.pdf'

# Función para obtener los datos del candidato
def obtener_datos_candidato(candidato_id):
    conn = mysql.connector.connect(
        host='mysql-contratos',
        user='juandejesus',
        password='lomaxp1204',
        database='contratos'
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM candidato WHERE id = %s", (candidato_id,))
    candidato = cursor.fetchone()
    conn.close()
    return candidato

# Función para generar el contrato en formato Word
def modificar_plantilla_word(candidato_data):
    # Cargar la plantilla de Word
    doc = Document(INPUT_WORD_PATH)
    
    # Buscar los marcadores y reemplazarlos con los datos del candidato
    for paragraph in doc.paragraphs:
        for key, value in candidato_data.items():
            marcador = f"[{key}]"  # Marcador en formato [key]
            if marcador in paragraph.text:
                paragraph.text = paragraph.text.replace(marcador, str(value))
    
    # Guardar el nuevo documento con los datos del candidato
    doc.save(OUTPUT_WORD_PATH)
    print("Plantilla de Word modificada y guardada correctamente.")

# Función para convertir el documento Word a PDF usando LibreOffice
def convertir_word_a_pdf():
    try:
        subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", OUTPUT_WORD_PATH, "--outdir", "/app/output"])
        print("Documento convertido a PDF exitosamente.")
    except Exception as e:
        print("Error al convertir el documento a PDF:", e)

# Función que se ejecuta al recibir un mensaje de RabbitMQ
def procesar_mensaje(ch, method, properties, body):
    # Decodificar el cuerpo del mensaje desde bytes a un diccionario
    mensaje = json.loads(body.decode('utf-8'))
    
    # Obtener el ID del usuario desde el diccionario
    candidato_id = int(mensaje['id_usuario'])
    print(f'Recibido ID de candidato: {candidato_id}')

    candidato_data = obtener_datos_candidato(candidato_id)
    if candidato_data:
        modificar_plantilla_word(candidato_data)
        convertir_word_a_pdf()
        print("Contrato generado en PDF.")

        # Actualizar el estado de impresión en la base de datos
        try:
            conn = mysql.connector.connect(
                host='mysql-contratos',
                user='juandejesus',
                password='lomaxp1204',
                database='contratos'
            )
            cursor = conn.cursor()
            cursor.execute("UPDATE candidato SET status_impresion = 1 WHERE id = %s", (candidato_id,))
            conn.commit()
            conn.close()
            print("Estado de impresión actualizado a 1.")
        except mysql.connector.Error as e:
            print("Error al actualizar el estado de impresión en la base de datos:", e)
    else:
        print("No se encontraron datos del candidato.")
    
    ch.basic_ack(delivery_tag=method.delivery_tag)

# Configuración de RabbitMQ y espera de mensajes
def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='rabbitmq',
        credentials=pika.PlainCredentials('juandejesus', 'lomaxp1204')
    ))

    channel = connection.channel()
    channel.queue_declare(queue= 'imprimir_contrato_queue')

    channel.basic_consume(queue= 'imprimir_contrato_queue', on_message_callback=procesar_mensaje)
    print('Esperando mensajes...')
    channel.start_consuming()

if __name__ == '__main__':
    main()
