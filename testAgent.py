from  Agent.MemoryAgent import MemoryAgent
from pathlib import Path


agent = MemoryAgent()
try:
# 修改为正确的测试数据路径
    CHAPTERS_PATH = "Resource\memory\story_plan"

    # 确保目录存在
    Path(CHAPTERS_PATH).mkdir(parents=True, exist_ok=True)
    print(f"章节数据目录: {CHAPTERS_PATH}")

    # 处理多章节数据
    for chapter_name, memories in agent.process_all_chapters(CHAPTERS_PATH):
        print(f"\n=== {chapter_name} 角色记忆 ===")
        for person_id, memory in memories.items():
            print(f"\n角色 {memory['character']['name']} 的记忆:")
            print(f"- 人际关系: {len(memory['relationships'])} 条")
            print(f"- 参与事件: {len(memory['events'])} 个")

    # 测试 get_previous_chapters_events 方法
    person_id = "p1"
    current_chapter = agent.current_chapter
    previous_events = agent.get_previous_chapters_events(person_id, current_chapter)
    print(f"\n{person_id} 在之前章节参与的事件:")
    for event in previous_events:
        print(f"章节: {event['chapter_label']}, 事件名称: {event['event_name']}, 事件顺序: {event['event_order']}")

    # 测试 get_next_chapters_events 方法
    next_events = agent.get_next_chapters_events(person_id, current_chapter)
    print(f"\n{person_id} 在之后章节参与的事件:")
    for event in next_events:
        print(f"章节: {event['chapter_label']}, 事件名称: {event['event_name']}, 事件顺序: {event['event_order']}")

finally:
    agent.close()