# Resource/template/story_plan_template.py

# JSON 结构模板 (空模板)
story_plan_template = {
    "relationships": [
        {
            "from_id": "",
            "to_id": "",
            "type": "",
            "intensity": None,
            "awareness": "",
            "new_detail": ""
        }
    ],
    "scenes": [
        {
            "id": "",
            "name": "",
            "place": "",
            "time_period": "",
            "atmosphere": ""
        }
    ],
    "events": [
        {
            "id": "",
            "name": "",
            "order": None,
            "scene_id": "",
            "details": "",
            "participants": [],
            "emotional_impact": {},
            "consequences": []
        }
    ]
}

# 完整示例
story_plan_example = {
    "relationships": [
        {
            "from_id": "p1",
            "to_id": "p2",
            "type": "债务关系",
            "intensity": 5,
            "awareness": "双方皆知",
            "new_detail": "借款金额增加"
        },
        {
            "from_id": "p2",
            "to_id": "p3",
            "type": "合作关系",
            "intensity": 3,
            "awareness": "单方知晓",
            "new_detail": "共享情报"
        }
    ],
    "scenes": [
        {
            "id": "s1",
            "name": "咖啡厅会面",
            "place": "市中心咖啡厅",
            "time_period": "AFTERNOON",
            "atmosphere": "轻松但暗藏紧张"
        },
        {
            "id": "s2",
            "name": "仓库对峙",
            "place": "废弃仓库",
            "time_period": "NIGHT",
            "atmosphere": "紧张危险"
        }
    ],
    "events": [
        {
            "id": "e1",
            "name": "秘密会面",
            "order": 1,
            "scene_id": "s1",
            "details": "p1和p2在咖啡厅讨论还款计划",
            "participants": ["p1", "p2"],
            "emotional_impact": {
                "p1": "焦虑",
                "p2": "自信"
            },
            "consequences": ["还款期限延长"]
        },
        {
            "id": "e2",
            "name": "意外相遇",
            "order": 2,
            "scene_id": "s1",
            "details": "p3偶然看到p1和p2的会面",
            "participants": ["p3"],
            "emotional_impact": {
                "p3": "好奇"
            },
            "consequences": ["p3开始调查"]
        }
    ]
}
