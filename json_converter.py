import json
import ast
from datetime import datetime

def _sanitize_item(item):
    """
    Recursively sanitizes an item to ensure it's JSON serializable.
    Converts non-string keys and non-serializable values to strings.
    """
    if isinstance(item, dict):
        new_dict = {}
        for k, v in item.items():
            # Ensure all keys that are not str, int, float, or bool are stringified.
            # Also, explicitly stringify bool keys as JSON requires string keys.
            if isinstance(k, bool) or not isinstance(k, (str, int, float)):
                new_key = str(k)
            else:
                new_key = k # It's already a str, int, or float (though int/float keys are not typical in JSON)

            # JSON standard requires keys to be strings.
            # If the key is int/float, json.dumps will convert it.
            # If it's a bool, we convert it to string here.
            if not isinstance(new_key, str):
                 new_key = str(new_key)

            new_dict[new_key] = _sanitize_item(v)
        return new_dict
    elif isinstance(item, list):
        return [_sanitize_item(i) for i in item]
    elif isinstance(item, (str, int, float, bool)) or item is None:
        return item
    elif isinstance(item, datetime):
        return item.isoformat()
    else:
        # For any other unrecognized type, convert to its string representation
        try:
            # Attempt to get a meaningful string representation
            return str(item)
        except Exception:
            # Fallback if str(item) fails for some reason
            return f"Unserializable object of type: {type(item).__name__}"

def parse_and_sanitize_json_string(json_string: str) -> str:
    """
    Parses a string that might be JSON, a Python dict/list, or slightly broken.
    Sanitizes it to be valid JSON, converting non-serializable objects to strings.

    Args:
        json_string: The input string to parse and sanitize.

    Returns:
        A valid JSON string.

    Raises:
        ValueError: If the input string cannot be processed into a JSON-compatible structure.
    """
    json_string = json_string.strip()
    data = None

    # Attempt 1: Try to load as is (valid JSON)
    try:
        data = json.loads(json_string)
    except json.JSONDecodeError:
        # Attempt 2: Try to evaluate as a Python literal (dict or list)
        try:
            # A common issue is single quotes instead of double quotes for strings
            # Or True/False/None instead of true/false/null
            # ast.literal_eval can handle these Python-specific literals
            data = ast.literal_eval(json_string)
        except (SyntaxError, ValueError, TypeError) as e_ast:
            # Attempt 3: Try some common fixes for "broken" JSON-like strings
            # Example: Trailing commas (Python allows, JSON standard does not)
            # For this, we might need more sophisticated repair logic if ast.literal_eval fails.
            # A simple approach for trailing commas in objects/arrays:
            temp_str = json_string
            if temp_str.endswith(','):
                temp_str = temp_str[:-1]

            # Try replacing Python bools/None with JSON equivalents
            temp_str = temp_str.replace('True', 'true').replace('False', 'false').replace('None', 'null')
            # Try replacing single quotes with double quotes (carefully, to avoid breaking already quoted strings)
            # This is tricky and can be error-prone. A better approach might involve regex.
            # For simplicity, we'll rely on ast.literal_eval for most Python dict/list cases.
            # If ast.literal_eval also fails, it's likely more complex than simple fixes.

            try:
                data = json.loads(temp_str) # Try loading again after simple fixes
            except json.JSONDecodeError:
                # If all attempts fail, raise an error
                raise ValueError(
                    "Input string could not be parsed as JSON or Python literal. "
                    f"JSONDecodeError: Original, AST Error: {e_ast}"
                ) from None

    if not isinstance(data, (dict, list)):
        # If the string parses to a single value (e.g. "123", "\"string\"")
        # and it's not a complex object, we still need to sanitize it if it's a custom object.
        # However, json.loads already handles primitive types correctly.
        # The _sanitize_item is more for complex nested structures.
        # If data is a simple type already, we just ensure it's dumped correctly.
        # If it was a string literal like "'datetime.now()'", ast.literal_eval would make it a string.
        # if it's a custom object that somehow passed json.loads or ast.literal_eval (unlikely for top level)
        # then sanitize it.
        sanitized_data = _sanitize_item(data)
    else:
        sanitized_data = _sanitize_item(data)

    return json.dumps(sanitized_data, indent=4)

if __name__ == '__main__':
    # Test cases
    test_strings = [
        ('{"name": "John", "age": 30, "city": "New York"}', "Valid JSON"),
        ("{'name': 'Jane', 'age': 25, 'city': 'London'}", "Python dict string with single quotes"),
        ('["apple", "banana", "cherry"]', "Valid JSON array"),
        ("['apple', 'banana', 'cherry']", "Python list string with single quotes"),
        ('{"item": "book", "details": {"pages": 200, "published": True}}', "Nested JSON"),
        ('{"item": "widget", "available": None}', "JSON with null (None)"),
        ('123', "JSON number"),
        ('"hello"', "JSON string"),
        ('true', "JSON boolean"),
        # Broken JSON / Python-like
        ('{"name": "Broken", "value":,}', "Broken JSON (trailing comma in object) - should fail or be fixed by more advanced logic"), # ast.literal_eval fails
        # ('["item1", "item2",]', "Broken JSON (trailing comma in array) - should fail or be fixed by more advanced logic"), # ast.literal_eval fails
        # Datetime object (will be stringified by _sanitize_item if passed as Python object)
        # For string input, it depends on how it's represented.
        # If it's `"{'date': datetime.datetime(2023, 1, 1)}"`, ast.literal_eval would fail directly.
        # We'll test object sanitization separately.
    ]

    print("--- Testing string inputs ---")
    for s, desc in test_strings:
        print(f"\nTesting: {desc}\nInput: {s}")
        try:
            result = parse_and_sanitize_json_string(s)
            print(f"Output:\n{result}")
        except ValueError as e:
            print(f"Error: {e}")

    print("\n--- Testing Python objects with sanitization ---")
    from datetime import date, time
    class Unserializable:
        def __init__(self, name):
            self.name = name
        def __str__(self):
            return f"Unserializable(name='{self.name}')"

    test_objects = [
        ({"key": datetime(2023, 10, 26, 10, 30, 0), 123: "value", "nes_ted": {"date_obj": date(2024,1,1)}}, "Dict with datetime and int key"),
        ([datetime(2023, 5, 15), {"time_obj": time(14, 45)}], "List with datetime and time object"),
        ({"obj": Unserializable("custom")}, "Dict with custom unserializable object"),
        ({(1,2): "tuple_key"}, "Dict with tuple key")
    ]

    for obj, desc in test_objects:
        print(f"\nTesting: {desc}\nInput Object: {obj}")
        try:
            # To test _sanitize_item directly with Python objects, we can simulate
            # the scenario where `data` is already a Python object post-parsing.
            # Then we pass it through json.dumps with _sanitize_item.
            # The `parse_and_sanitize_json_string` is designed for string inputs.
            # So, we'll directly use json.dumps with a default handler for this test.

            # Simulating how parse_and_sanitize_json_string would use _sanitize_item
            sanitized_obj = _sanitize_item(obj)
            result = json.dumps(sanitized_obj, indent=4)
            print(f"Output:\n{result}")
        except Exception as e:
            print(f"Error during object sanitization test: {e}")

    # Example of a string that ast.literal_eval can handle but json.loads can't
    python_dict_str_ok_for_ast = "{'value': True, 'items': [1, None, 'text']}"
    print(f"\nTesting Python dict string (ok for ast.literal_eval):\nInput: {python_dict_str_ok_for_ast}")
    try:
        result = parse_and_sanitize_json_string(python_dict_str_ok_for_ast)
        print(f"Output:\n{result}")
    except ValueError as e:
        print(f"Error: {e}")

    # Example of slightly broken JSON (trailing comma) that ast.literal_eval might handle for lists/dicts
    # Note: ast.literal_eval does NOT support trailing commas in dicts/lists directly.
    # The "fix" in the code is very basic.
    broken_json_trailing_comma_list = '["item1", "item2",]'
    print(f"\nTesting broken JSON (trailing comma in list):\nInput: {broken_json_trailing_comma_list}")
    try:
        # This specific case will fail with current logic as ast.literal_eval doesn't allow trailing comma
        # and json.loads doesn't either. The simple temp_str[:-1] only works if the whole string ends with comma.
        # A more robust trailing comma remover would be needed.
        # For now, expecting this to fail or be misparsed by simple fixes.
        result = parse_and_sanitize_json_string(broken_json_trailing_comma_list)
        print(f"Output:\n{result}")
    except ValueError as e:
        print(f"Error: {e}") # Expected

def convert_file_to_json(file_path: str) -> str:
    """
    Reads a file, parses its content (expecting JSON or Python literal string),
    sanitizes it, and returns a valid JSON string.

    Args:
        file_path: The path to the input file.

    Returns:
        A valid JSON string.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file content cannot be processed.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return parse_and_sanitize_json_string(content)
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: File not found at '{file_path}'")
    except Exception as e: # Catch other potential errors from parse_and_sanitize_json_string
        raise ValueError(f"Error processing file '{file_path}': {e}")


if __name__ == '__main__':
    # ... (previous test cases remain unchanged) ...
    # Test cases
    test_strings = [
        ('{"name": "John", "age": 30, "city": "New York"}', "Valid JSON"),
        ("{'name': 'Jane', 'age': 25, 'city': 'London'}", "Python dict string with single quotes"),
        ('["apple", "banana", "cherry"]', "Valid JSON array"),
        ("['apple', 'banana', 'cherry']", "Python list string with single quotes"),
        ('{"item": "book", "details": {"pages": 200, "published": True}}', "Nested JSON"),
        ('{"item": "widget", "available": None}', "JSON with null (None)"),
        ('123', "JSON number"),
        ('"hello"', "JSON string"),
        ('true', "JSON boolean"),
        # Broken JSON / Python-like
        ('{"name": "Broken", "value":,}', "Broken JSON (trailing comma in object) - should fail or be fixed by more advanced logic"), # ast.literal_eval fails
        # ('["item1", "item2",]', "Broken JSON (trailing comma in array) - should fail or be fixed by more advanced logic"), # ast.literal_eval fails
        # Datetime object (will be stringified by _sanitize_item if passed as Python object)
        # For string input, it depends on how it's represented.
        # If it's `"{'date': datetime.datetime(2023, 1, 1)}"`, ast.literal_eval would fail directly.
        # We'll test object sanitization separately.
    ]

    print("--- Testing string inputs ---")
    for s, desc in test_strings:
        print(f"\nTesting: {desc}\nInput: {s}")
        try:
            result = parse_and_sanitize_json_string(s)
            print(f"Output:\n{result}")
        except ValueError as e:
            print(f"Error: {e}")

    print("\n--- Testing Python objects with sanitization ---")
    from datetime import date, time
    class Unserializable:
        def __init__(self, name):
            self.name = name
        def __str__(self):
            return f"Unserializable(name='{self.name}')"

    test_objects = [
        ({"key": datetime(2023, 10, 26, 10, 30, 0), 123: "value", "nes_ted": {"date_obj": date(2024,1,1)}}, "Dict with datetime and int key"),
        ([datetime(2023, 5, 15), {"time_obj": time(14, 45)}], "List with datetime and time object"),
        ({"obj": Unserializable("custom")}, "Dict with custom unserializable object"),
        ({(1,2): "tuple_key"}, "Dict with tuple key")
    ]

    for obj, desc in test_objects:
        print(f"\nTesting: {desc}\nInput Object: {obj}")
        try:
            # To test _sanitize_item directly with Python objects, we can simulate
            # the scenario where `data` is already a Python object post-parsing.
            # Then we pass it through json.dumps with _sanitize_item.
            # The `parse_and_sanitize_json_string` is designed for string inputs.
            # So, we'll directly use json.dumps with a default handler for this test.

            # Simulating how parse_and_sanitize_json_string would use _sanitize_item
            sanitized_obj = _sanitize_item(obj)
            result = json.dumps(sanitized_obj, indent=4)
            print(f"Output:\n{result}")
        except Exception as e:
            print(f"Error during object sanitization test: {e}")

    # Example of a string that ast.literal_eval can handle but json.loads can't
    python_dict_str_ok_for_ast = "{'value': True, 'items': [1, None, 'text']}"
    print(f"\nTesting Python dict string (ok for ast.literal_eval):\nInput: {python_dict_str_ok_for_ast}")
    try:
        result = parse_and_sanitize_json_string(python_dict_str_ok_for_ast)
        print(f"Output:\n{result}")
    except ValueError as e:
        print(f"Error: {e}")

    # Example of slightly broken JSON (trailing comma) that ast.literal_eval might handle for lists/dicts
    # Note: ast.literal_eval does NOT support trailing commas in dicts/lists directly.
    # The "fix" in the code is very basic.
    broken_json_trailing_comma_list = '["item1", "item2",]'
    print(f"\nTesting broken JSON (trailing comma in list):\nInput: {broken_json_trailing_comma_list}")
    try:
        # This specific case will fail with current logic as ast.literal_eval doesn't allow trailing comma
        # and json.loads doesn't either. The simple temp_str[:-1] only works if the whole string ends with comma.
        # A more robust trailing comma remover would be needed.
        # For now, expecting this to fail or be misparsed by simple fixes.
        result = parse_and_sanitize_json_string(broken_json_trailing_comma_list)
        print(f"Output:\n{result}")
    except ValueError as e:
        print(f"Error: {e}") # Expected

    broken_json_trailing_comma_dict = '{"key1":"value1","key2":"value2",}'
    print(f"\nTesting broken JSON (trailing comma in dict):\nInput: {broken_json_trailing_comma_dict}")
    try:
        result = parse_and_sanitize_json_string(broken_json_trailing_comma_dict)
        print(f"Output:\n{result}")
    except ValueError as e:
        print(f"Error: {e}") # Expected

    # --- Test file functionality ---
    print("\n--- Testing file input ---")
    # Create a dummy test file
    test_file_content_valid = '{"message": "Hello from file", "count": 100, "valid": true}'
    test_file_content_python_literal = "{'message': 'Hello from python file', 'count': 200, 'valid': None}"
    test_file_content_broken = '{"message": "Broken file", "error": True,}' # Trailing comma

    dummy_file_valid = "test_input_valid.json"
    dummy_file_python = "test_input_python.txt"
    dummy_file_broken = "test_input_broken.json"

    with open(dummy_file_valid, "w", encoding="utf-8") as f:
        f.write(test_file_content_valid)
    with open(dummy_file_python, "w", encoding="utf-8") as f:
        f.write(test_file_content_python_literal)
    with open(dummy_file_broken, "w", encoding="utf-8") as f:
        f.write(test_file_content_broken)

    file_tests = [
        (dummy_file_valid, "Valid JSON file"),
        (dummy_file_python, "Python literal file"),
        (dummy_file_broken, "Broken JSON file (trailing comma)"),
        ("non_existent_file.json", "Non-existent file")
    ]

    for file_path, desc in file_tests:
        print(f"\nTesting: {desc}\nFile: {file_path}")
        try:
            result = convert_file_to_json(file_path)
            print(f"Output:\n{result}")
        except (FileNotFoundError, ValueError) as e:
            print(f"Error: {e}")

    # Clean up dummy files
    import os
    if os.path.exists(dummy_file_valid):
        os.remove(dummy_file_valid)
    if os.path.exists(dummy_file_python):
        os.remove(dummy_file_python)
    if os.path.exists(dummy_file_broken):
        os.remove(dummy_file_broken)

def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Convert a JSON-like string or file to a well-formatted JSON output. "
                    "Handles Python dict/list strings, and sanitizes non-serializable objects."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-s", "--string",
        type=str,
        help="Input string to convert (e.g., '{\"key\": \"value\"}' or \"{'key': True}\")."
    )
    group.add_argument(
        "-f", "--file",
        type=str,
        help="Path to an input file containing the JSON-like string."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Path to an output file. If not provided, output is printed to stdout."
    )

    args = parser.parse_args()

    output_json = None
    try:
        if args.string:
            output_json = parse_and_sanitize_json_string(args.string)
        elif args.file:
            output_json = convert_file_to_json(args.file)

        if output_json:
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f_out:
                    f_out.write(output_json)
                print(f"Successfully converted and saved to '{args.output}'")
            else:
                print(output_json)

    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    # --- Test string inputs ---
    # ... (string input tests remain the same) ...
    test_strings = [
        ('{"name": "John", "age": 30, "city": "New York"}', "Valid JSON"),
        ("{'name': 'Jane', 'age': 25, 'city': 'London'}", "Python dict string with single quotes"),
        ('["apple", "banana", "cherry"]', "Valid JSON array"),
        ("['apple', 'banana', 'cherry']", "Python list string with single quotes"),
        ('{"item": "book", "details": {"pages": 200, "published": True}}', "Nested JSON"),
        ('{"item": "widget", "available": None}', "JSON with null (None)"),
        ('123', "JSON number"),
        ('"hello"', "JSON string"),
        ('true', "JSON boolean"),
        ('{"name": "Broken", "value":,}', "Broken JSON (trailing comma in object)"),
    ]

    # print("--- Testing string inputs ---")
    # for s, desc in test_strings:
    #     print(f"\nTesting: {desc}\nInput: {s}")
    #     try:
    #         result = parse_and_sanitize_json_string(s)
    #         print(f"Output:\n{result}")
    #     except ValueError as e:
    #         print(f"Error: {e}")

    # --- Testing Python objects with sanitization ---
    # ... (object sanitization tests remain the same) ...
    from datetime import date, time # Ensure these are imported if running this block
    class Unserializable:
        def __init__(self, name):
            self.name = name
        def __str__(self):
            return f"Unserializable(name='{self.name}')"

    test_objects = [
        ({"key": datetime(2023, 10, 26, 10, 30, 0), 123: "value", "nes_ted": {"date_obj": date(2024,1,1)}}, "Dict with datetime and int key"),
        ([datetime(2023, 5, 15), {"time_obj": time(14, 45)}], "List with datetime and time object"),
        ({"obj": Unserializable("custom")}, "Dict with custom unserializable object"),
        ({(1,2): "tuple_key"}, "Dict with tuple key")
    ]
    # print("\n--- Testing Python objects with sanitization ---")
    # for obj, desc in test_objects:
    #     print(f"\nTesting: {desc}\nInput Object: {obj}")
    #     try:
    #         sanitized_obj = _sanitize_item(obj)
    #         result = json.dumps(sanitized_obj, indent=4)
    #         print(f"Output:\n{result}")
    #     except Exception as e:
    #         print(f"Error during object sanitization test: {e}")

    # ... (other specific string tests remain the same) ...
    # python_dict_str_ok_for_ast = "{'value': True, 'items': [1, None, 'text']}"
    # print(f"\nTesting Python dict string (ok for ast.literal_eval):\nInput: {python_dict_str_ok_for_ast}")
    # try:
    #     result = parse_and_sanitize_json_string(python_dict_str_ok_for_ast)
    #     print(f"Output:\n{result}")
    # except ValueError as e:
    #     print(f"Error: {e}")

    # broken_json_trailing_comma_list = '["item1", "item2",]'
    # print(f"\nTesting broken JSON (trailing comma in list):\nInput: {broken_json_trailing_comma_list}")
    # try:
    #     result = parse_and_sanitize_json_string(broken_json_trailing_comma_list)
    #     print(f"Output:\n{result}")
    # except ValueError as e:
    #     print(f"Error: {e}")

    # broken_json_trailing_comma_dict = '{"key1":"value1","key2":"value2",}'
    # print(f"\nTesting broken JSON (trailing comma in dict):\nInput: {broken_json_trailing_comma_dict}")
    # try:
    #     result = parse_and_sanitize_json_string(broken_json_trailing_comma_dict)
    #     print(f"Output:\n{result}")
    # except ValueError as e:
    #     print(f"Error: {e}")

    # --- Test file functionality ---
    # print("\n--- Testing file input ---")
    # Create a dummy test file
    test_file_content_valid = '{"message": "Hello from file", "count": 100, "valid": true}'
    test_file_content_python_literal = "{'message': 'Hello from python file', 'count': 200, 'valid': None}"
    test_file_content_broken = '{"message": "Broken file", "error": True,}' # Trailing comma

    dummy_file_valid = "test_input_valid.json"
    dummy_file_python = "test_input_python.txt"
    dummy_file_broken = "test_input_broken.json"

    # with open(dummy_file_valid, "w", encoding="utf-8") as f:
    #     f.write(test_file_content_valid)
    # with open(dummy_file_python, "w", encoding="utf-8") as f:
    #     f.write(test_file_content_python_literal)
    # with open(dummy_file_broken, "w", encoding="utf-8") as f:
    #     f.write(test_file_content_broken)

    file_tests = [
        (dummy_file_valid, "Valid JSON file"),
        (dummy_file_python, "Python literal file"),
        (dummy_file_broken, "Broken JSON file (trailing comma)"),
        ("non_existent_file.json", "Non-existent file")
    ]

    # for file_path, desc in file_tests:
    #     print(f"\nTesting: {desc}\nFile: {file_path}")
    #     try:
    #         result = convert_file_to_json(file_path)
    #         print(f"Output:\n{result}")
    #     except (FileNotFoundError, ValueError) as e:
    #         print(f"Error: {e}")

    # Clean up dummy files
    # import os # Already imported
    # if os.path.exists(dummy_file_valid):
    #     os.remove(dummy_file_valid)
    # if os.path.exists(dummy_file_python):
    #     os.remove(dummy_file_python)
    # if os.path.exists(dummy_file_broken):
    #     os.remove(dummy_file_broken)

    # Call main to enable CLI when script is run directly
    main()

    broken_json_trailing_comma_dict = '{"key1":"value1","key2":"value2",}'
    print(f"\nTesting broken JSON (trailing comma in dict):\nInput: {broken_json_trailing_comma_dict}")
    try:
        result = parse_and_sanitize_json_string(broken_json_trailing_comma_dict)
        print(f"Output:\n{result}")
    except ValueError as e:
        print(f"Error: {e}") # Expected
