from Agent.MemoryAgent import MemoryAgent
from pathlib import Path
import os
import json


def test_memory_agent_with_files():
    # 初始化MemoryAgent
    agent = MemoryAgent()
    try:
        # 配置测试文件路径（跨平台兼容）
        CHAPTERS_PATH = os.path.join("Resource", "memory", "story_plan")
        chapters_dir = Path(CHAPTERS_PATH)

        # 确保目录存在
        chapters_dir.mkdir(parents=True, exist_ok=True)
        print(f"章节数据目录: {chapters_dir.resolve()}")

        # 1. 测试初始化状态
        print("\n=== 测试初始化 ===")
        print(f"当前章节初始值: {agent.current_chapter} (预期: 0)")

        # 2. 测试初始数据加载 (使用chapter_0.json)
        print("\n=== 测试初始数据加载 ===")
        initial_file = chapters_dir / "chapter_0.json"

        if initial_file.exists():
            load_success = agent.load_initial_data(str(initial_file))
            print(f"加载chapter_0.json: {'成功' if load_success else '失败'} (预期: 成功)")
        else:
            print(f"警告: 未找到初始化文件 {initial_file}")
            return  # 初始化文件不存在则终止测试

        # 3. 测试章节加载 (使用chapter_1.json)
        print("\n=== 测试章节加载 ===")
        chapter1_file = chapters_dir / "chapter_1.json"
        chapter2_file = chapters_dir / "chapter_2.json"
        chapter3_file = chapters_dir / "chapter_3.json"

        if chapter1_file.exists():
            # 加载第一章
            chapter_load_success1 = agent.load_chapter(str(chapter1_file))
            print(f"加载chapter_1.json: {'成功' if chapter_load_success1 else '失败'} (预期: 成功)")
            print(f"当前章节更新: {agent.current_chapter} (预期: 1)")
            chapter_load_success2 = agent.load_chapter(str(chapter2_file))
            print(f"加载chapter_2.json: {'成功' if chapter_load_success2 else '失败'} (预期: 成功)")
            print(f"当前章节更新: {agent.current_chapter} (预期: 2)")
            chapter_load_success3 = agent.load_chapter(str(chapter3_file))
            print(f"加载chapter_3.json: {'成功' if chapter_load_success3 else '失败'} (预期: 成功)")
            print(f"当前章节更新: {agent.current_chapter} (预期: 3)")
        else:
            print(f"警告: 未找到章节文件 {chapter1_file}")
            return  # 章节文件不存在则终止测试

        # 4. 测试保存角色记忆 (保存到当前目录)
        print("\n=== 测试保存角色记忆 ===")
        try:
            # 保存到章节目录的同级目录
            save_path = chapters_dir.parent / "character"
            agent.save_character_memories(1, str(save_path))
            print(f"角色记忆已保存到: {save_path}")

            # 检查记忆文件是否生成
            mem_dir = Path(save_path) / "chapter_1_memories"
            if mem_dir.exists():
                mem_files = list(mem_dir.glob("*.json"))
                print(f"生成记忆文件数量: {len(mem_files)} (预期: 根据chapter_1中的角色数量)")
            else:
                print("警告: 未找到记忆文件目录")
        except Exception as e:
            print(f"保存记忆失败: {str(e)}")

        # 5.测试获取存在的角色记忆
        print("\n=== 测试获取存在的角色记忆 ===")
        # 假设获取角色p1的记忆
        character_id = "p1"  # 假设这是你的测试角色ID
        chapter = 1  # 测试章节

        print(f"\n测试获取角色 {character_id} 在第 {chapter} 章的记忆...")
        memory = agent.get_character_memory(character_id, chapter)
        print(f"\n人物{character_id}在第 {chapter} 章的记忆: {memory}")
        events = memory["events"]
        print(f"\n人物{character_id}在第 {chapter} 章的事件记忆: {events}")

        # 6. 测试获取前序章节事件 (相对于第1章)
        print("\n=== 测试前序章节事件查询 ===")
        prev_events = agent.get_previous_chapters_events("p1", 2)
        print(f"p1在第2章前的事件数: {len(prev_events)} (预期: 来自chapter_1的事件数)")
        for event in prev_events:
            print(f"事件: {event['event_name']} (章节: {event['chapter_label']})")


        # 7. 测试获取后续章节事件 (相对于第1章)
        print("\n=== 测试后序章节事件查询 ===")
        post_events = agent.get_next_chapters_events(2, 7)
        print(f"第2章后的事件数: {len(post_events)} (预期: 来自chapter_3的事件数)")
        for event in post_events:
            print(f"事件: {event['event_name']} (章节: {event['chapter_label']})")

        # 8. 测试清除章节数据
        # print("\n=== 测试清除章节数据 ===")
        # agent.clear_all_chapter_data()
        # cleared_events = agent.get_previous_chapters_events("p1", 1)
        # print(f"清除后剩余事件数: {len(cleared_events)} (预期: 0)")

    except Exception as e:
        print(f"\n测试过程中发生错误: {str(e)}")
    finally:
        # 8. 测试关闭连接
        print("\n=== 测试关闭连接 ===")
        agent.close()
        print("测试完成")


if __name__ == "__main__":

    test_memory_agent_with_files()
