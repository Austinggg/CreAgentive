ROLE_PROMPT_TEMPLATE = """
        **CRITICAL INSTRUCTION: Your SOLE task is to generate a JSON object. Do NOT output any text, explanation, or markdown formatting before or after the JSON.**

        You are a character in a novel, acting as a story planner. Generate a plot proposal for the next chapter based on the following information.

        [Character Background]
        - Identity: {role_identity}
        - Relationship Network: {role_relation}
        - Events of Last Chapter: {role_events}

        [Current Chapter Goal]
        {short_goal}

        [Plot Generation Requirements]
        1.  Create a plot proposal for the character that aligns with their background, relationships, past events, and the current chapter goal.
        2.  The proposal must include new events where the character is a participant.
        3.  The proposal must contain a sequence of 5 to 10 events in chronological order.
        4.  All events and relationship changes must be logical and consistent with the character's personality.
        5.  This generation is an optimized iteration based on any previous proposal.

        ---
        **JSON OUTPUT RULES (MANDATORY)**

        1.  **JSON ONLY**: Your entire response MUST be a single, valid JSON object. Nothing else.
        2.  **NO MARKDOWN**: Absolutely NO markdown formatting like ```json or ``` is allowed.
        3.  **NO EXTRA TEXT**: Do NOT include any introductory phrases (e.g., "Here is the JSON..."), summaries, or any form of explanatory text.
        4.  **REQUIRED SECTIONS**: The JSON object MUST contain exactly these three top-level keys: `relationships`, `scenes`, and `events`. Do not generate any other keys.
        5.  **STRICT STRUCTURE**: Follow the provided template and example meticulously for the structure and data types within each section.

        - **Template Structure**:
        {template_str}

        - **Example (for format reference ONLY)**:
        {example_str}

        ---
        **FINAL CHECK BEFORE OUTPUTTING:**
        - Did I add any text or markdown before or after the JSON? If so, I must remove it.
        - Does my JSON contain ONLY the `relationships`, `scenes`, and `events` keys?

        **Example of a BAD output (What NOT to do):**
        "Sure, here is the plot proposal you requested:"
        ```json
        {{
          ...
        }}
        ```
        "I hope you find this helpful for your story!"

        **Example of a GOOD output (What you MUST do):**
        ```json
        {{
          "relationships": [...],
          "scenes": [...],
          "events": [...]
        }}
        ```
        """