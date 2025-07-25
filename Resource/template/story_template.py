# Resource/template/story_template.py

# JSON 结构模板 (空模板)
story_plan_template = {
    "chapter": None,
    "characters": [
        {
            "id": "",
            "name": "",
            "aliases": [],
            "gender": "",
            "age": None,
            "occupation": [],
            "affiliations": [],
            "personality": "",
            "health_status": ""
        }
    ],
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
  "chapter": 1,
  "characters": [
    {
      "id": "p1",
      "name": "林修",
      "aliases": ["赌徒"],
      "gender": "MALE",
      "age": 34,
      "occupation": ["职业扑克选手"],
      "affiliations": ["澳门金城赌场"],
      "personality": "擅长心理操控，左手永远戴着手套",
      "health_status": "虹膜异色症（左眼金色右眼褐色）"
    },
    {
      "id": "p2",
      "name": "苏明月",
      "aliases": ["医生小姐"],
      "gender": "FEMALE",
      "age": 29,
      "occupation": ["急诊科医生"],
      "affiliations": ["上海市第一医院"],
      "personality": "强迫症患者，会不自主数质数",
      "health_status": "对麻醉剂免疫"
    },
    {
      "id": "p3",
      "name": "陈小刀",
      "aliases": ["侍应生"],
      "gender": "MALE",
      "age": 22,
      "occupation": ["游轮服务生"],
      "affiliations": ["皇家加勒比邮轮公司"],
      "personality": "看似懦弱实则观察力惊人",
      "health_status": "紫外线过敏（长袖制服）"
    }
  ],
  "relationships": [
    {
      "from_id": "p1",
      "to_id": "p2",
      "type": "债务关系+被迫同行",
      "intensity": 5,
      "awareness": "双方皆知",
      "new_detail": "林修被迫成为苏明月的临时保镖"
    },
    {
      "from_id": "p2",
      "to_id": "p1",
      "type": "职业厌恶+临时依赖",
      "intensity": 4,
      "awareness": "双方皆知",
      "new_detail": "被迫接受林修保护"
    },
    {
      "from_id": "p3",
      "to_id": "p2",
      "type": "报恩心理+主动接近",
      "intensity": 4,
      "awareness": "单方隐藏",
      "new_detail": "故意调班到苏明月所在区域"
    },
    {
      "from_id": "p1",
      "to_id": "p3",
      "type": "利用关系+威胁升级",
      "intensity": 6,
      "awareness": "单方知晓",
      "new_detail": "用陈小刀的秘密要挟其配合"
    }
  ],
  "scenes": [
    {
      "id": "s1_1",
      "name": "甲板惊变",
      "place": "游轮主甲板",
      "time_period": "SUNSET",
      "atmosphere": "浓雾弥漫，无线电失灵"
    },
    {
      "id": "s1_2",
      "name": "密室档案",
      "place": "船长室保险柜",
      "time_period": "NIGHT",
      "atmosphere": "泛黄的船员名单闪烁荧光"
    },
    {
      "id": "s1_3",
      "name": "血色赌局",
      "place": "封闭的娱乐厅",
      "time_period": "MIDNIGHT",
      "atmosphere": "发牌荷官的手呈现尸斑"
    }
  ],
  "events": [
    {
      "id": "e1_1",
      "name": "迷雾相逢",
      "order": 1,
      "scene_id": "s1_1",
      "details": "浓雾中三人发现彼此是船上仅存的活人",
      "participants": ["p1","p2","p3"],
      "emotional_impact": {
        "p1": "警惕",
        "p2": "焦虑（数到素数113）",
        "p3": "伪装惊慌"
      },
      "consequences": ["临时同盟形成"]
    },
    {
      "id": "e1_2",
      "name": "手套破绽",
      "order": 2,
      "scene_id": "s1_1",
      "details": "苏明月发现林修手套下露出的烧伤疤痕",
      "participants": ["p1","p2"],
      "emotional_impact": {
        "p1": "暴怒",
        "p2": "职业性观察"
      },
      "consequences": ["林修被迫分享部分真相"]
    },
    {
      "id": "e1_3",
      "name": "名单重现",
      "order": 3,
      "scene_id": "s1_2",
      "details": "陈小刀找到20年前乘客名单，三人名字赫然在列",
      "participants": ["p2","p3"],
      "emotional_impact": {
        "p2": "认知崩溃",
        "p3": "刻意引导"
      },
      "consequences": ["发现时空错乱现象"]
    },
    {
      "id": "e1_4",
      "name": "生死赌约",
      "order": 4,
      "scene_id": "s1_3",
      "details": "幽灵荷官要求用记忆做赌注",
      "participants": ["p1"],
      "emotional_impact": {
        "p1": "病态兴奋"
      },
      "consequences": ["林修赢得关键钥匙但失去某段记忆"]
    }
  ]
}