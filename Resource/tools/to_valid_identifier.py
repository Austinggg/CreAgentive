import re

def to_valid_identifier(name):
    # 去除非法字符，只保留字母、数字、下划线
    cleaned = re.sub(r'[^\w]', '_', name)
    # 如果首字符是数字，则前面加个前缀
    if cleaned and cleaned[0].isdigit():
        cleaned = cleaned
    # 如果还是不合法，就 fallback 成默认名
    if not cleaned.isidentifier():
        cleaned = "default_agent"
    return cleaned