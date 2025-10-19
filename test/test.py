import requests

# Dirección de la API de LibreTranslate por defecto
API_URL = "http://localhost:5000/translate"

def run_translation_test():
    """
    Realiza una prueba de traducción simple de inglés a español.
    """
    test_data = {
        "q": "Hello, how are you?",
        "source": "en",
        "target": "es",
        "format": "text"
    }
    
    # Intenta hacer la petición
    try:
        print("Intentando contactar con el servidor en:", API_URL)
        response = requests.post(API_URL, json=test_data, timeout=10)
        response.raise_for_status() # Lanza una excepción para códigos de estado erróneos (4xx o 5xx)
        
        result = response.json()
        translated_text = result.get("translatedText", "Traducción no encontrada")
        
        print("\n--- Test de Funcionamiento ---")
        print(f"Texto original (en): {test_data['q']}")
        print(f"Texto traducido (es): {translated_text}")
        
        # Validación simple
        if "hola" in translated_text.lower():
            print("\n✅ ¡Test de traducción exitoso!")
        else:
            print("\n⚠️ Test de traducción incompleto o inesperado.")

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: No se pudo conectar con LibreTranslate.")
        print("Asegúrate de que el servidor esté corriendo (ejecuta start_server.sh primero).")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ ERROR en la petición: {e}")

if __name__ == "__main__":
    # Opcional: espera unos segundos si ejecutas el script de test inmediatamente después de arrancar el servidor
    # para darle tiempo a LibreTranslate a cargar los modelos.
    # time.sleep(5) 
    run_translation_test()
