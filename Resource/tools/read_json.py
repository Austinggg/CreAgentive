import os
import re
import json
from typing import Dict, List, Optional

def _read_json_file(file_path: str) -> Dict:
    """读取并解析JSON文件（私有辅助函数）"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件 {file_path} 不存在")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"无法解析 JSON 文件 {file_path}: {e}")

def read_json(file_path: str) -> Dict:
    """
    读取指定路径的 JSON 文件
    
    Args:
        file_path: JSON 文件的完整路径
        
    Returns:
        解析后的 JSON 数据
    """
    return _read_json_file(file_path)

def read_max_index_file(folder_path: str) -> Dict:
    """
    读取文件夹中序号最大的 JSON 文件
    
    Args:
        folder_path: 包含 JSON 文件的文件夹路径
        
    Returns:
        解析后的 JSON 数据
    """
    # 获取所有 JSON 文件
    files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
    if not files:
        raise FileNotFoundError("文件夹中没有 .json 文件")
    
    # 使用 max 查找最大序号文件
    def get_index(filename: str) -> int:
        match = re.search(r'\d+', filename)
        # 如果没有数字部分则返回 -1
        return int(match.group()) if match else -1
    
    
    max_file = max(files, key=get_index)
    max_number = get_index(max_file) # 最大编号
    file_path = os.path.join(folder_path, max_file)
    
    # 读取并返回文件内容
    return _read_json_file(file_path), max_number