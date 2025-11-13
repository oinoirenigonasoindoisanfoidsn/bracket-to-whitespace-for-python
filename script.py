import tokenize
import io
import sys

def get_protected_positions(code):
    """Returns a set of (line_index, char_index) inside strings or comments."""
    protected = set()
    lines = code.splitlines(keepends=True)
    try:
        for token in tokenize.generate_tokens(io.StringIO(code).readline):
            if token.type in (tokenize.STRING, tokenize.COMMENT):
                sl, sc = token.start
                el, ec = token.end
                sl -= 1; el -= 1  # 0-based line index
                if sl == el:
                    for c in range(sc, ec):
                        protected.add((sl, c))
                else:
                    for line_idx in range(sl, el + 1):
                        if line_idx >= len(lines):
                            continue
                        line_len = len(lines[line_idx])
                        if line_idx == sl:
                            start_col, end_col = sc, line_len
                        elif line_idx == el:
                            start_col, end_col = 0, min(ec, line_len)
                        else:
                            start_col, end_col = 0, line_len
                        for c in range(start_col, end_col):
                            protected.add((line_idx, c))
    except (tokenize.TokenError, ValueError):
        pass
    return protected

def extract_comment_after_brace(text):
    """Extract comment part after a brace, if any."""
    stripped = text.lstrip()
    if stripped.startswith('#'):
        return stripped
    if '#' in stripped:
        return stripped[stripped.index('#'):]
    return ''

def is_scoping_open_brace(line, pos, line_idx, protected):
    if (line_idx, pos) in protected:
        return False

    # Check if it's after a colon with only whitespace/comment after
    before = line[:pos]
    after = line[pos+1:]

    if ':' in before:
        last_colon_idx = before.rindex(':')
        between = before[last_colon_idx+1:]
        if between.strip() == '':  # only whitespace between : and {
            after_clean = after.strip()
            if after_clean == '' or after_clean.startswith('#'):
                return True

    # Or line is just '{' (with optional comment)
    stripped = line.strip()
    if stripped == '{' or (stripped.startswith('{') and extract_comment_after_brace(stripped[1:])):
        return True

    return False

def is_scoping_close_brace(line, pos, line_idx, protected):
    if (line_idx, pos) in protected:
        return False

    stripped = line.strip()
    if stripped == '}':
        return True
    if stripped.startswith('}'):
        after = stripped[1:]
        if after.lstrip() == '' or after.lstrip().startswith('#'):
            return True
    return False

def convert_curly_to_indented(code):
    if not code.strip():
        return code

    lines = code.splitlines(keepends=False)
    protected = get_protected_positions(code)
    output_lines = []
    indent_level = 0

    for line_idx, orig_line in enumerate(lines):
        line = orig_line
        i = 0
        found_scoping_brace = False
        comment = ''

        # Scan for scoping braces
        while i < len(line):
            if line[i] == '{' and is_scoping_open_brace(line, i, line_idx, protected):
                # Preserve everything before {
                before = line[:i].rstrip()
                after = line[i+1:]
                comment = extract_comment_after_brace(after)

                # Emit the 'before' part (e.g., 'if x:')
                if before or comment:
                    new_line = before
                    if comment:
                        new_line += ('  ' if before else '') + comment
                    output_lines.append(new_line)

                indent_level += 1
                found_scoping_brace = True
                break

            elif line[i] == '}' and is_scoping_close_brace(line, i, line_idx, protected):
                indent_level = max(0, indent_level - 1)
                after = line[i+1:]
                comment = extract_comment_after_brace(after)

                # Only emit line if there's a comment
                if comment:
                    output_lines.append(("    " * indent_level) + comment)
                # Otherwise, emit nothing (skip empty line)

                found_scoping_brace = True
                break

            i += 1

        if not found_scoping_brace:
            # Regular line: apply current indentation
            stripped = line.lstrip()
            if stripped:
                output_lines.append(("    " * indent_level) + stripped)
            else:
                # Preserve truly blank lines (user might want them)
                output_lines.append('')

    # Post-process: remove runs of multiple blank lines down to at most one
    cleaned_lines = []
    for line in output_lines:
        if line == '' and cleaned_lines and cleaned_lines[-1] == '':
            continue  # skip consecutive blank lines
        cleaned_lines.append(line)

    # Reconstruct result
    result = '\n'.join(cleaned_lines)
    if code.endswith('\n'):
        result += '\n'
    return result

def main():
    try:
        with open('curlied.py', 'r', encoding='utf-8') as f:
            original_code = f.read()
    except FileNotFoundError:
        print("❌ Error: 'curlied.py' not found.", file=sys.stderr)
        return

    try:
        converted_code = convert_curly_to_indented(original_code)
        with open('whitespaced.py', 'w', encoding='utf-8') as f:
            f.write(converted_code)
        print("✅ Successfully converted 'curlied.py' → 'whitespaced.py'")
    except Exception as e:
        print(f"❌ Conversion failed: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()