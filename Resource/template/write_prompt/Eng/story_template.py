# JSON structure template (empty template)
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

# Complete example
story_plan_example = {
    "relationships": [
        {
            "from_id": "p1",
            "to_id": "p2",
            "type": "Debt Relationship",
            "intensity": 5,
            "awareness": "Mutually Aware",
            "new_detail": "Loan amount increased"
        },
        {
            "from_id": "p2",
            "to_id": "p3",
            "type": "Cooperative Relationship",
            "intensity": 3,
            "awareness": "Unilaterally Aware",
            "new_detail": "Intelligence shared"
        }
    ],
    "scenes": [
        {
            "id": "s1",
            "name": "Café Meeting",
            "place": "Downtown Café",
            "time_period": "AFTERNOON",
            "atmosphere": "Relaxed but with underlying tension"
        },
        {
            "id": "s2",
            "name": "Warehouse Standoff",
            "place": "Abandoned Warehouse",
            "time_period": "NIGHT",
            "atmosphere": "Tense and dangerous"
        }
    ],
    "events": [
        {
            "id": "e1",
            "name": "Secret Meeting",
            "order": 1,
            "scene_id": "s1",
            "details": "p1 and p2 discuss the repayment plan at the café",
            "participants": ["p1", "p2"],
            "emotional_impact": {
                "p1": "Anxious",
                "p2": "Confident"
            },
            "consequences": ["Repayment deadline extended"]
        },
        {
            "id": "e2",
            "name": "Unexpected Encounter",
            "order": 2,
            "scene_id": "s1",
            "details": "p3 happens to see p1 and p2's meeting",
            "participants": ["p3"],
            "emotional_impact": {
                "p3": "Curious"
            },
            "consequences": ["p3 starts investigating"]
        }
    ]
}