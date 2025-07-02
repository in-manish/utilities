import unittest
import json
import os
from datetime import datetime, date, time
from json_converter import parse_and_sanitize_json_string, convert_file_to_json, _sanitize_item

# Helper class for testing unserializable objects
class UnserializableObject:
    def __init__(self, name="test"):
        self.name = name
    def __str__(self):
        return f"UnserializableObject(name='{self.name}')"

class TestJSONConverter(unittest.TestCase):

    def test_parse_valid_json_string(self):
        json_str = '{"name": "John Doe", "age": 30, "isStudent": false, "courses": [{"title": "History", "credits": 3}]}'
        expected_dict = {"name": "John Doe", "age": 30, "isStudent": False, "courses": [{"title": "History", "credits": 3}]}
        result_str = parse_and_sanitize_json_string(json_str)
        self.assertEqual(json.loads(result_str), expected_dict)

    def test_parse_python_dict_string(self):
        py_dict_str = "{'name': 'Jane Doe', 'age': 28, 'isStudent': True, 'misc': None, 'city': 'London'}"
        expected_dict = {"name": "Jane Doe", "age": 28, "isStudent": True, "misc": None, "city": "London"}
        result_str = parse_and_sanitize_json_string(py_dict_str)
        self.assertEqual(json.loads(result_str), expected_dict)

    def test_parse_python_list_string(self):
        py_list_str = "['apple', {'key': 'value'}, True, None, 123]"
        expected_list = ["apple", {"key": "value"}, True, None, 123]
        result_str = parse_and_sanitize_json_string(py_list_str)
        self.assertEqual(json.loads(result_str), expected_list)

    def test_sanitize_datetime_object_in_string(self):
        # This test relies on _sanitize_item being called internally by parse_and_sanitize_json_string
        # when a Python object is constructed by ast.literal_eval
        # However, ast.literal_eval cannot directly evaluate a string containing 'datetime(...)'.
        # So, we test _sanitize_item directly for this.
        dt = datetime(2023, 1, 1, 12, 30, 0)
        obj_with_dt = {"event_time": dt, "name": "Meeting"}

        # Simulate the data after ast.literal_eval or json.loads would have produced a Python object
        sanitized_obj = _sanitize_item(obj_with_dt)
        result_json_str = json.dumps(sanitized_obj) # parse_and_sanitize_json_string does this

        loaded_result = json.loads(result_json_str)
        self.assertEqual(loaded_result["name"], "Meeting")
        self.assertEqual(loaded_result["event_time"], dt.isoformat())

    def test_sanitize_date_and_time_objects(self):
        d = date(2024, 3, 15)
        t = time(10, 0, 0)
        obj_with_date_time = {"event_date": d, "event_start_time": t}
        sanitized = _sanitize_item(obj_with_date_time)
        result_json_str = json.dumps(sanitized)
        loaded_result = json.loads(result_json_str)
        self.assertEqual(loaded_result["event_date"], str(d)) # date.isoformat() or str(date)
        self.assertEqual(loaded_result["event_start_time"], str(t)) # time.isoformat() or str(time)


    def test_sanitize_unserializable_object_to_string(self):
        custom_obj = UnserializableObject("MyCustomObj")
        data = {"item": custom_obj, "id": 1}
        sanitized_data = _sanitize_item(data)
        # We expect the custom_obj to be converted to its string representation
        self.assertEqual(sanitized_data["item"], str(custom_obj))
        self.assertEqual(sanitized_data["id"], 1)
        # Check if it dumps to JSON
        json_output = json.dumps(sanitized_data)
        reloaded = json.loads(json_output)
        self.assertEqual(reloaded["item"], str(custom_obj))


    def test_sanitize_non_string_keys(self):
        data = {123: "numeric_key", True: "boolean_key", (1,2): "tuple_key"}
        sanitized_data = _sanitize_item(data)
        self.assertIn("123", sanitized_data)
        self.assertEqual(sanitized_data["123"], "numeric_key")
        self.assertIn("True", sanitized_data) # Note: 'True' (string) not True (boolean)
        self.assertEqual(sanitized_data["True"], "boolean_key")
        self.assertIn("(1, 2)", sanitized_data)
        self.assertEqual(sanitized_data["(1, 2)"], "tuple_key")

    def test_broken_json_string_trailing_comma_simple_fix(self):
        # Test the simple fix: 'value,' -> 'value' if at the end of the string
        # This is a very basic fix and might not cover all cases.
        # ast.literal_eval cannot handle trailing commas in dicts/lists.
        # json.loads cannot handle them either.
        # The current implementation has a very naive fix for a trailing comma if it's the last char of the string.
        # '{"a":1,}' -> '{"a":1}'
        broken_str = '{"key": "value",}'
        expected_dict = {"key": "value"}
        try:
            result_str = parse_and_sanitize_json_string(broken_str)
            self.assertEqual(json.loads(result_str), expected_dict)
        except ValueError as e:
            self.fail(f"Trailing comma simple fix failed: {e}")

    def test_broken_json_string_python_keywords(self):
        broken_str = '{"valid": True, "empty": None}'
        expected_dict = {"valid": True, "empty": None}
        # The replace 'True'->'true', 'None'->'null' should handle this before json.loads
        result_str = parse_and_sanitize_json_string(broken_str)
        self.assertEqual(json.loads(result_str), expected_dict)


    def test_invalid_json_string_should_raise_value_error(self):
        invalid_str = '{"key": "value"' # Missing closing brace
        with self.assertRaises(ValueError):
            parse_and_sanitize_json_string(invalid_str)

        invalid_str_2 = '{key_no_quotes: "value"}' # Key without quotes
        with self.assertRaises(ValueError):
            parse_and_sanitize_json_string(invalid_str_2)

        invalid_str_3 = '{"name": "Broken", "value":,}' # Trailing comma not at the very end
        with self.assertRaises(ValueError):
            parse_and_sanitize_json_string(invalid_str_3)


    # File tests
    def setUp(self):
        # Create dummy files for file tests
        self.test_dir = "test_converter_temp_files"
        os.makedirs(self.test_dir, exist_ok=True)

        self.valid_json_file = os.path.join(self.test_dir, "valid.json")
        with open(self.valid_json_file, "w") as f:
            f.write('{"message": "Hello", "count": 10}')

        self.python_literal_file = os.path.join(self.test_dir, "python.txt")
        with open(self.python_literal_file, "w") as f:
            f.write("{'message': 'Hi there', 'items': [1, True, None]}")

        self.broken_file_trailing_comma = os.path.join(self.test_dir, "broken_comma.json")
        with open(self.broken_file_trailing_comma, "w") as f:
            f.write('{"data": [1,2,3],}') # Test the simple end-of-string comma fix

        self.empty_file = os.path.join(self.test_dir, "empty.json")
        with open(self.empty_file, "w") as f:
            f.write("") # Empty content

    def tearDown(self):
        # Clean up dummy files
        if os.path.exists(self.valid_json_file):
            os.remove(self.valid_json_file)
        if os.path.exists(self.python_literal_file):
            os.remove(self.python_literal_file)
        if os.path.exists(self.broken_file_trailing_comma):
            os.remove(self.broken_file_trailing_comma)
        if os.path.exists(self.empty_file):
            os.remove(self.empty_file)
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)

    def test_convert_valid_json_file(self):
        expected_dict = {"message": "Hello", "count": 10}
        result_str = convert_file_to_json(self.valid_json_file)
        self.assertEqual(json.loads(result_str), expected_dict)

    def test_convert_python_literal_file(self):
        expected_dict = {"message": "Hi there", "items": [1, True, None]}
        result_str = convert_file_to_json(self.python_literal_file)
        self.assertEqual(json.loads(result_str), expected_dict)

    def test_convert_broken_json_file_trailing_comma_fix(self):
        expected_dict = {"data": [1,2,3]}
        result_str = convert_file_to_json(self.broken_file_trailing_comma)
        self.assertEqual(json.loads(result_str), expected_dict)

    def test_convert_non_existent_file(self):
        with self.assertRaises(FileNotFoundError):
            convert_file_to_json("non_existent_file.json")

    def test_convert_empty_file(self):
        # An empty file is not valid JSON or Python literal
        with self.assertRaises(ValueError):
            convert_file_to_json(self.empty_file)

    def test_parse_simple_literals(self):
        self.assertEqual(json.loads(parse_and_sanitize_json_string("123")), 123)
        self.assertEqual(json.loads(parse_and_sanitize_json_string('"string"')), "string")
        self.assertEqual(json.loads(parse_and_sanitize_json_string("true")), True)
        self.assertEqual(json.loads(parse_and_sanitize_json_string("null")), None)
        self.assertEqual(json.loads(parse_and_sanitize_json_string("[]")), [])
        self.assertEqual(json.loads(parse_and_sanitize_json_string("{}")), {})


if __name__ == '__main__':
    unittest.main()
