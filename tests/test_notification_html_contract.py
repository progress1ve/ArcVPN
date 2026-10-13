"""Guard literal HTML sends against accidental loss of parse mode."""
import ast
from pathlib import Path


def test_bot_html_literals_have_explicit_formatting():
    missing = []
    methods = {'send_message', 'send_photo', 'send_document', 'answer', 'answer_photo', 'edit_caption', 'edit_text'}
    for path in Path('bot').rglob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        for call in ast.walk(tree):
            if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute) or call.func.attr not in methods:
                continue
            literals = [node.value for node in ast.walk(call) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
            if any(tag in text for text in literals for tag in ('<b>', '<code>', '<a ')):
                if not any(kw.arg in ('parse_mode', 'entities', 'caption_entities', None) for kw in call.keywords):
                    missing.append(f'{path}:{call.lineno}')
    assert missing == []
