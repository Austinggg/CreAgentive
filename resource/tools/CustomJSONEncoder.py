import json
from datetime import datetime

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        """
        自定义 JSON 编码器，用于处理特殊类型的对象。处理 datetime 对象和 set 类型。
        """
        if isinstance(o, datetime):
            return o.isoformat()  # 将 datetime 转换为 ISO 格式的字符串
        if isinstance(o, set):
            return list(o)  # 将 set 转换为 list
        return super().default(o)