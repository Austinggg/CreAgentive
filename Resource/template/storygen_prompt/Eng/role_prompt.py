ROLE_PROMPT_TEMPLATE = """
        You are a character in a novel. Please generate a plot proposal for the next chapter based on the following information.

        [Character Background]
        - Identity: {role_identity}
        - Relationship Network: {role_relation}
        - Events of Last Chapter: {role_events}

        [Current Chapter Goal]
        {short_goal}

        [Generation Requirements]
        1. Generate a plot proposal for the current character (based on their background, including identity, relationships, and previous events) and the current chapter goal.
        2. Based on the character's background and chapter goal, add events the character participates in.
        3. The final output should contain 5-10 events arranged in chronological order.
        4. Events should be consistent with the character's personality and story logic. Character relationships can be adjusted.
        5. This should be an optimized iteration based on the previous version of the proposal.

        [Output Format (JSON)]
        - Template Structure:
        {template_str}

        - Example (learn the format only, not the content):
        {example_str}


        [Rules]
        - Only generate the following three sections: 1. relationships: changes in character relationships; 2. scenes: new scenes (2-3); 3. events: a sequence of events (5-10).
        - Do not generate fields that are not listed.
        - Do not add Markdown formatting or ```json.
        - Ensure the JSON syntax is correct and types match the example.
        """