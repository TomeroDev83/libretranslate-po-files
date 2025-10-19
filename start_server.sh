#!/bin/bash
# Script para iniciar LibreTranslate solo con inglés y español,
# con un parámetro opcional para actualizar los modelos.

# 1. Definir los argumentos base
LOAD_ARGS="--load-only en,es"
UPDATE_FLAG=""

# 2. Comprobar si se proporcionó el parámetro 'update'
if [ "$1" == "update" ]; then
    UPDATE_FLAG="--update-models"
    echo "Parámetro 'update' detectado. Se actualizarán los modelos."
else
    echo "Parámetro 'update' no detectado. Se iniciará el servidor con los modelos existentes."
fi

# 3. Mostrar información de inicio
echo "Iniciando LibreTranslate en http://localhost:5000 con los modelos en,es..."

# 4. Ejecutar LibreTranslate con los argumentos combinados
exec libretranslate $LOAD_ARGS $UPDATE_FLAG
