from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from docx import Document
import mysql.connector
import json
import pika
import subprocess
import requests
import time

# Ruta para guardar el archivo Word y el PDF
INPUT_WORD_PATH = '/app/templates/contrato.docx'
OUTPUT_WORD_PATH = '/app/output/contrato_generado.docx'
OUTPUT_PDF_PATH = '/app/output/contrato_generado.pdf'

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
        # Convertir a PDF usando LibreOffice
        subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", OUTPUT_WORD_PATH, "--outdir", "/app/output"], check=True)
        print("Documento convertido a PDF exitosamente.")
    except subprocess.CalledProcessError as e:
        print(f"Error al convertir Word a PDF: {e}")
        raise Exception("Error al generar el PDF.")

def enviar_pdf_a_laravel(candidato_id):
    try:
        # Verificar si el PDF está listo
        if not os.path.exists(OUTPUT_PDF_PATH):
            print(f"PDF no encontrado: {OUTPUT_PDF_PATH}")
            raise Exception("El PDF no se generó correctamente.")
        
        # Subir el PDF a Laravel
        with open(OUTPUT_PDF_PATH, 'rb') as pdf_file:
            response = requests.post(
                'http://php-apache-contratos/api/upload-pdf',
                files={'file': pdf_file},
                data={'candidato_id': candidato_id},
                timeout=5
            )
            if response.status_code == 200:
                print("PDF enviado exitosamente a Laravel.")
                # Eliminar el archivo PDF local
                os.remove(OUTPUT_PDF_PATH)
            else:
                print(f"Error al enviar PDF a Laravel: {response.status_code}")
                raise Exception("Falló la comunicación con Laravel.")
    except Exception as e:
        print(f"Ocurrió un error: {e}")
        raise




def verificar_descarga_pdf(candidato_id):
    if not os.path.exists(OUTPUT_PDF_PATH):
        print("El archivo PDF ya no existe en el sistema. Procediendo a actualizar el estado.")
        # Código para actualizar el estado de impresión en la base de datos
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

# Función que se ejecuta al recibir un mensaje de RabbitMQ
def procesar_mensaje(ch, method, properties, body):
    try:
        mensaje = json.loads(body.decode('utf-8'))
        candidato_id = int(mensaje['id_usuario'])

        # Obtener datos del candidato
        candidato_data = obtener_datos_candidato(candidato_id)
        if not candidato_data:
            print(f"Candidato con ID {candidato_id} no encontrado.")
            return

        # Modificar Word y convertir a PDF
        modificar_plantilla_word(candidato_data)
        convertir_word_a_pdf()

        # Subir PDF a Laravel
        enviar_pdf_a_laravel(candidato_id)
        verificar_descarga_pdf(candidato_id)

        

        print(f"Contrato procesado correctamente para el candidato {candidato_id}.")
    except Exception as e:
        print(f"Error al procesar mensaje: {e}")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


   

# Configuración de RabbitMQ y espera de mensajes
def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='rabbitmq',
        credentials=pika.PlainCredentials('juandejesus', 'lomaxp1204')
    ))

    channel = connection.channel()
    channel.queue_declare(queue= 'imprimir_contrato_queue',durable=True)

    channel.basic_consume(queue= 'imprimir_contrato_queue', on_message_callback=procesar_mensaje)
    print('Esperando mensajes...')
    channel.start_consuming()

if __name__ == '__main__':
    main()
