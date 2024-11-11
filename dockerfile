# Usar la imagen base de Python
FROM python:3.10-slim

# Instalar dependencias necesarias para pdfkit y wkhtmltopdf
RUN apt-get update && apt-get install -y \
    libreoffice \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists\
    libfreetype6-dev \
    libx11-dev \
    libxml2-dev \
    libxslt-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar las librerías de Python necesarias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de la aplicación
COPY . /app

# Exponer el puerto si es necesario
EXPOSE 5000

# Comando de inicio
CMD ["tail", "-f", "/dev/null"]
