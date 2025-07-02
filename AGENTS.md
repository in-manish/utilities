## JSON Converter Utility (`json_converter.py`)

This utility converts JSON-like strings or files into well-formatted, sanitized JSON. It can handle Python dictionary/list string representations and attempts to clean up minor syntactical issues. Non-serializable objects (like datetime) within the data are converted to their string representations.

### Running the Utility

The script provides a command-line interface:

```bash
python json_converter.py [options]
```

**Options:**

*   **Input (required, choose one):**
    *   `-s STRING, --string STRING`: Provide the input string directly.
        *Example:* `python json_converter.py -s "{'key': 'value', 'items': [1, True, None]}"`
    *   `-f FILE, --file FILE`: Provide the path to an input file containing the JSON-like string.
        *Example:* `python json_converter.py -f ./my_data.txt`

*   **Output (optional):**
    *   `-o OUTPUT_FILE, --output OUTPUT_FILE`: Specify a file to save the converted JSON output. If omitted, the output is printed to the standard console.
        *Example:* `python json_converter.py -f ./my_data.txt -o ./formatted_output.json`

### Development

**Running Tests:**

The utility includes a suite of unit tests located in `test_json_converter.py`. To run the tests, use the `unittest` module:

```bash
python -m unittest test_json_converter.py
```

Or, for more verbose output:

```bash
python -m unittest -v test_json_converter.py
```

Ensure all tests pass after making any changes to `json_converter.py`.

**Key Functionality:**

*   `parse_and_sanitize_json_string(json_string)`: Core function for parsing and sanitizing string inputs.
*   `convert_file_to_json(file_path)`: Handles file inputs.
*   `_sanitize_item(item)`: Recursively sanitizes Python objects to ensure they are JSON serializable (e.g., converts `datetime` to string, non-string keys to strings).

**Coding Conventions:**

*   Follow standard Python (PEP 8) guidelines.
*   Ensure new functionality is accompanied by relevant unit tests.
*   Prioritize clarity and robustness in parsing and error handling.
*   When modifying parsing logic, consider edge cases for "broken" JSON or Python literal strings.
```
