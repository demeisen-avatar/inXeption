#!/usr/bin/env python3
# ruff: noqa: T201 - Allow print statements in this development tool
import os
import re
import sys
from typing import Any, Dict, List


class BlueprintValidationError(Exception):
    '''Exception raised for blueprint validation errors.'''


def extract_md_chunks(file_path: str) -> List[Dict[str, Any]]:
    '''Extract blueprint chunks from markdown files.'''
    with open(file_path) as f:
        lines = f.readlines()

    starts = [
        i for i, line in enumerate(lines) if line.strip() and line.strip()[0] == '💙'
    ]
    ends = [
        i for i, line in enumerate(lines) if line.strip() and line.strip()[0] == '🖤'
    ]

    # Simple validation - must have matching pairs in the right order
    is_good = len(starts) == len(ends) and all(
        start < end for start, end in zip(starts, ends)
    )
    if not is_good:
        raise BlueprintValidationError(f'Mismatched 💙 and 🖤 markers in {file_path}')

    return [
        {
            'file': file_path,
            'line': start + 1,
            'content': ''.join(lines[start : end + 1]),
        }
        for start, end in zip(starts, ends)
    ]


def extract_sh_chunks(file_path: str) -> List[Dict[str, Any]]:
    '''Extract blueprint chunks from shell scripts.'''
    with open(file_path) as f:
        lines = f.readlines()

    chunks = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Look for shell comments with 💙 - allow for space after #
        if line.startswith('#') and '💙' in line:
            start = i
            # Find end of comment block
            while i + 1 < len(lines) and lines[i + 1].strip().startswith('#'):
                i += 1
            content = ''.join(lines[start : i + 1])
            chunks.append({'file': file_path, 'line': start + 1, 'content': content})
        i += 1

    return chunks


def extract_py_chunks(file_path: str) -> List[Dict[str, Any]]:
    '''Extract blueprint chunks from Python files using AST for accurate structure parsing.'''
    import ast

    # Define TRIPLE at the beginning of the function so it's available throughout
    TRIPLE = r"'" * 3  # prevent precommit-checks from messing with triple-quotes

    with open(file_path) as f:
        content = f.read()

    chunks = []
    lines = content.splitlines()

    # First extract comment blueprints (AST won't help with comments)
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#') and '🔵' in line:
            start = i
            while i + 1 < len(lines) and lines[i + 1].strip().startswith('#'):
                i += 1
            comment_content = '\n'.join(lines[start : i + 1])
            chunks.append(
                {'file': file_path, 'line': start + 1, 'content': comment_content}
            )
        i += 1

    # Now use AST to extract docstring blueprints with proper context
    try:
        tree = ast.parse(content)

        # Process module-level docstring first
        module_docstring = ast.get_docstring(tree)
        if module_docstring and '💙' in module_docstring:
            # Module-level docstring with blueprint
            chunks.append(
                {
                    'file': file_path,
                    'line': 1,  # Module docstrings are always at line 1
                    'content': TRIPLE + module_docstring + TRIPLE,
                }
            )

        # Visit all function and class nodes to extract docstrings
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                docstring = ast.get_docstring(node)
                if docstring and '💙' in docstring:
                    # Found a function/class with a blueprint in its docstring
                    line_num = node.lineno

                    # Get the function/class definition from source
                    if isinstance(node, ast.FunctionDef):
                        definition = f"def {node.name}({', '.join(a.arg for a in node.args.args)}):"
                    else:  # ClassDef
                        definition = f'class {node.name}:'

                    chunks.append(
                        {
                            'file': file_path,
                            'line': line_num,
                            'content': definition + '\n' + TRIPLE + docstring + TRIPLE,
                        }
                    )

    except SyntaxError:
        # If AST parsing fails, fall back to regex-based extraction for docstrings
        TRIPLE = r"'" * 3  # prevent precommit-checks from messing with triple-quotes
        docstring_pattern = f'{TRIPLE}([\\s\\S]*?💙[\\s\\S]*?){TRIPLE}'
        for match in re.finditer(docstring_pattern, content):
            line_num = content[: match.start()].count('\n') + 1
            chunks.append(
                {'file': file_path, 'line': line_num, 'content': match.group(0)}
            )

    return chunks


def validate_index(chunk: Dict[str, Any]) -> Dict[str, Any]:
    '''Validate and add index to a chunk.'''
    content = chunk['content']

    # Check for index - works for all three file types
    index_match = re.search(r'[💙🔵](\d+\.\d+)?', content)

    if index_match and index_match.group(1):
        chunk['index'] = float(index_match.group(1))
    else:
        raise BlueprintValidationError(
            f'Blueprint at {chunk["file"]}:{chunk["line"]} missing valid index'
        )

    return chunk


def process_directory(path: str, check_mode: bool = False) -> List[Dict[str, Any]]:
    '''Process directory or single file, collecting blueprint chunks.'''
    all_chunks = []
    errors = []
    failed_files = set()

    if os.path.isfile(path):
        files = [path]
    else:
        files = []
        for root, _, filenames in os.walk(path):
            for filename in filenames:
                if any(filename.endswith(ext) for ext in ['.py', '.md', '.sh']):
                    files.append(os.path.join(root, filename))

    # Process files by extension
    extractors = {
        '.md': extract_md_chunks,
        '.sh': extract_sh_chunks,
        '.py': extract_py_chunks,
    }

    for file_path in files:
        _, ext = os.path.splitext(file_path)
        extractor = extractors.get(ext)
        if extractor:
            try:
                chunks = extractor(file_path)
                all_chunks.extend(chunks)
            except BlueprintValidationError as e:
                errors.append(str(e))
                failed_files.add(file_path)
                if not check_mode:
                    print(f'⛔️ {str(e)}')
                continue

    # Validate all chunks
    valid_chunks = []
    for chunk in all_chunks:
        try:
            validated = validate_index(chunk)
            valid_chunks.append(validated)
        except BlueprintValidationError as e:
            errors.append(str(e))
            failed_files.add(chunk['file'])
            if not check_mode:
                print(f'⛔️ {str(e)}')
            continue

    # Sort by index
    sorted_chunks = sorted(valid_chunks, key=lambda x: x['index'])

    if check_mode and errors:
        for error in errors:
            print(f'⛔️ {error}')
        sys.exit(1)

    return sorted_chunks, failed_files


def main():
    '''Main entry point for blueprint validation.'''
    import argparse

    # Add inXeption directory to path for imports
    inxeption_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'inXeption'
    )
    sys.path.append(inxeption_path)
    from inXeption.utils.yaml_utils import dump_str

    parser = argparse.ArgumentParser(description='Blueprint validation tool')
    parser.add_argument(
        'path', nargs='?', default=os.getcwd(), help='File or directory to scan'
    )
    parser.add_argument('--check', action='store_true', help='Validate blueprints only')
    args = parser.parse_args()

    try:
        chunks, failed_files = process_directory(args.path, args.check)

        if args.check:
            if not failed_files:
                print('✅ Blueprint validation passed.')
                sys.exit(0)
            else:
                # This should be covered by process_directory's error handling
                sys.exit(1)
        else:
            # In extraction mode, print out the found blueprints
            if chunks:
                print(
                    f'\nFound {len(chunks)} blueprint{"s" if len(chunks) != 1 else ""}:'
                )

                # Format using a nice dictionary structure for YAML output
                output_dict = {}
                for chunk in chunks:
                    key = f"{chunk['file']}:{chunk['line']}"
                    output_dict[key] = chunk['content']

                # Format using YAML utils
                formatted_output = dump_str(output_dict)
                print(formatted_output)

                print(f'\n{" - " * 7}')
            else:
                print('\nNo valid blueprints found.')

            # Report any failed files
            if failed_files:
                print(
                    f'\nFound {len(failed_files)} file{"s" if len(failed_files) != 1 else ""} with blueprint validation issues.'
                )

            # Exit with appropriate code in extraction mode - still succeed even with some failures
            sys.exit(0)

    except BlueprintValidationError as e:
        print(f'⛔️ {str(e)}')
        sys.exit(1)
    except Exception as e:
        print(f'⛔️ Unexpected error: {str(e)}')
        sys.exit(1)


if __name__ == '__main__':
    main()
