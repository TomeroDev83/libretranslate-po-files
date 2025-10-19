# PO/POT File Translator

A Python tool to translate PO/POT files using LibreTranslate. This project provides utilities to extract msgid strings from PO/POT files and translate them using a local LibreTranslate instance.

## Prerequisites

- Python 3.6+
- pip3
- LibreTranslate

## Installation

1. Install LibreTranslate:
```bash
pip3 install libretranslate
```

2. Clone this repository:
```bash
git clone <repository-url>
cd libretranslate-pot-translator
```

3. Install Python dependencies:
```bash
pip3 install requests polib
```

## Starting the Translation Server

1. Start the LibreTranslate server using the provided script:
```bash
./start_server.sh
```

This will start LibreTranslate with English and Spanish language support on http://localhost:5000

To update the translation models, use:
```bash
./start_server.sh update
```

## Usage

### Basic Translation

To translate a PO/POT file:

```bash
python3 traductor.py -i input.pot -o translations.txt
```

### Command Line Options

- `-i, --input`: Input PO/POT file (default: es_nexudus.po)
- `-o, --output`: Output file for translations (default: traducciones_es.txt)
- `-u, --url`: LibreTranslate API URL (default: http://localhost:5000/translate)
- `-s, --source`: Source language (default: en)
- `-t, --target`: Target language (default: es)
- `-w, --workers`: Number of concurrent translation workers (default: 4)
- `--continue-on-error`: Continue processing even if some translations fail
- `--debug`: Enable debug logging

### Testing the Server

To verify the translation server is working:

```bash
python3 test/test.py
```

## Output Format

The translations are saved in a text file with the following format:

```
ORIGINAL: English text
TRADUCCIÓN: Translated text

ORIGINAL: Another English text
TRADUCCIÓN: Another translated text
```

## Features

- Concurrent translation processing
- Robust PO/POT file parsing
- Fallback parser when polib is not available
- Atomic file writing
- Retry mechanism for failed requests
- Progress logging

## Error Handling

- Connection errors to LibreTranslate server
- Invalid PO/POT file formats
- Network timeouts
- Translation API errors

## License

MIT
