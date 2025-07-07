# 创作需求模板结构
demand_template = {
    "title": None,             # 小说标题
    "genre": None,             # 题材类型，如：奇幻、科幻、悬疑等
    "background": None,        # 故事背景（世界观/时代/地点/环境）
    "style": None,             # 目标文风，如：严肃、轻松等
    "character_count": None,   # 主要人物数量
    "language_tone": None      # 语言风格，如：华丽、简洁、幽默等
}

# 初始化信息模板
init_info_template = {
    "applied_template": None,      # 实际应用的需求模板内容
    "config_items": {},            # 初始化生成的配置项（如章节、结构等）
    "characters": [],              # 主要角色列表，建议为列表结构
    "operator": None,              # 执行初始化的操作人或Agent名称
    "remark": None                 # 备注或补充说明
}