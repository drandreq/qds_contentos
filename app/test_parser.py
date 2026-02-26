from core.mp_dialect_parser import compiler
import json

metadata = compiler.parse_markdown_file("/vault/01_course/test_lesson.md")
print("SUCCESS!")
print(metadata.model_dump_json(indent=2))
