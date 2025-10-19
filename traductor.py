import argparse
import json
import logging
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_URL = "http://localhost:5000/translate"
DEFAULT_INPUT = "es_nexudus.po"
DEFAULT_OUTPUT = "traducciones_es.txt"
DEFAULT_SOURCE = "en"
DEFAULT_TARGET = "es"
DEFAULT_WORKERS = 4
MAX_TEXT_LENGTH = 5000  # evita enviar textos demasiado largos en una sola petición

logger = logging.getLogger(__name__)


def make_session(retries: int = 3, backoff: float = 0.5, status_forcelist=(500, 502, 503, 504)) -> requests.Session:
    s = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff, status_forcelist=status_forcelist, allowed_methods=frozenset(['POST', 'GET']))
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


def extract_msgids(file_path: Path) -> List[str]:
    """
    Extrae msgid de un .po/.pot. Usa polib si está instalado; si no, hace un parse tolerante
    que soporta continuaciones:
        msgid "primera parte"
        "segunda parte"
    """
    try:
        import polib  # tipo: ignore
    except Exception:
        logger.debug("polib no disponible: usando parser alternativo.")
        return _extract_msgids_fallback(file_path)

    po = polib.pofile(str(file_path))
    texts = []
    for entry in po:
        # Solo msgid (no msgid_plural) y no vacío
        if entry.msgid and not entry.obsolete:
            texts.append(entry.msgid)
    return texts


def _extract_msgids_fallback(file_path: Path) -> List[str]:
    pattern_start = re.compile(r'^msgid\s+"(.*)"\s*$')
    pattern_cont = re.compile(r'^"(.*)"\s*$')
    texts: List[str] = []
    with file_path.open('r', encoding='utf-8') as f:
        collecting = False
        buffer_parts: List[str] = []
        for raw in f:
            line = raw.rstrip("\n")
            if not collecting:
                m = pattern_start.match(line)
                if m:
                    collecting = True
                    buffer_parts = [m.group(1)]
                    # immediate empty msgid check allowed (skip)
                    if buffer_parts == ['']:
                        collecting = False
                        buffer_parts = []
                # else ignore
            else:
                m2 = pattern_cont.match(line)
                if m2:
                    buffer_parts.append(m2.group(1))
                else:
                    # end of continued msgid
                    full = ''.join(buffer_parts)
                    # Unescape sequences \" and others
                    full = full.encode('utf-8').decode('unicode_escape')
                    if full:
                        texts.append(full)
                    collecting = False
                    buffer_parts = []
                    # re-check this line in case it starts a new msgid
                    m = pattern_start.match(line)
                    if m:
                        collecting = True
                        buffer_parts = [m.group(1)]
        # EOF: flush
        if collecting and buffer_parts:
            full = ''.join(buffer_parts)
            full = full.encode('utf-8').decode('unicode_escape')
            if full:
                texts.append(full)
    return texts


def validate_response(resp_json: dict) -> Optional[str]:
    """
    Devuelve el texto traducido si se encuentra en la respuesta esperada.
    Se valida la longitud y tipos.
    """
    if not isinstance(resp_json, dict):
        return None
    # LibreTranslate estándar usa 'translatedText'
    translated = resp_json.get("translatedText") or resp_json.get("translation") or resp_json.get("text")
    if isinstance(translated, str) and translated.strip():
        return translated.strip()
    return None


def translate_text(session: requests.Session, url: str, text: str, source: str, target: str, timeout: int = 15) -> Optional[str]:
    if not text:
        return ""
    if len(text) > MAX_TEXT_LENGTH:
        logger.warning("Texto demasiado largo (%d), truncando.", len(text))
        text = text[:MAX_TEXT_LENGTH]
    payload = {"q": text, "source": source, "target": target, "format": "text"}
    try:
        r = session.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        translated = validate_response(data)
        if translated is None:
            logger.error("Respuesta inesperada de traducción para texto: %r -> %s", text[:60], json.dumps(data)[:200])
        return translated
    except requests.exceptions.RequestException as e:
        logger.error("Error al traducir: %s", e)
        return None


def write_atomic(path: Path, content: str):
    """
    Escribe de forma atómica: escribe en fichero temporal y reemplaza.
    """
    path_parent = path.parent
    path_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(path_parent), delete=False) as tmp:
        tmp.write(content)
        tmp_name = tmp.name
    os.replace(tmp_name, str(path))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Traducir msgid de un .po/.pot usando LibreTranslate")
    parser.add_argument("--input", "-i", default=DEFAULT_INPUT, help="Archivo .po/.pot de entrada")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT, help="Archivo de salida")
    parser.add_argument("--url", "-u", default=DEFAULT_URL, help="URL de la API de LibreTranslate")
    parser.add_argument("--source", "-s", default=DEFAULT_SOURCE, help="Idioma origen")
    parser.add_argument("--target", "-t", default=DEFAULT_TARGET, help="Idioma destino")
    parser.add_argument("--workers", "-w", type=int, default=DEFAULT_WORKERS, help="Hilos concurrentes")
    parser.add_argument("--continue-on-error", action="store_true", help="No abortar si una petición falla")
    parser.add_argument("--debug", action="store_true", help="Modo debug (logging)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format="%(levelname)s: %(message)s")

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Archivo de entrada no encontrado: %s", input_path)
        return 2

    msgids = extract_msgids(input_path)
    if not msgids:
        logger.info("No se encontraron msgid para traducir.")
        return 0

    logger.info("Encontrados %d msgid.", len(msgids))

    session = make_session()
    results: List[str] = []
    futures = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        for msg in msgids:
            futures.append(ex.submit(translate_text, session, args.url, msg, args.source, args.target))
        for fut, original in zip(futures, msgids):
            translated = fut.result()
            if translated is None:
                logger.error("Traducción fallida para: %.40s...", original)
                if not args.continue_on_error:
                    logger.error("Abortando por fallo de traducción.")
                    return 3
                else:
                    translated = "<ERROR>"
            results.append(f"ORIGINAL: {original}")
            results.append(f"TRADUCCIÓN: {translated}\n")

    output_path = Path(args.output)
    try:
        write_atomic(output_path, "\n".join(results))
        logger.info("Traducción completada. Resultados guardados en %s", output_path)
    except OSError as e:
        logger.error("No se pudo escribir el archivo de salida: %s", e)
        return 4

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
