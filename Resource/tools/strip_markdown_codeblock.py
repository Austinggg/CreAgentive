def strip_markdown_codeblock(text: str) -> str:
    """
    去除 LLM 输出中的 Markdown 代码块标记（如 ```json 和 ```），保留纯净 JSON 字符串。
    """
    lines = text.strip().splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()