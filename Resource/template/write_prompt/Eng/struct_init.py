# Creative demand template structure
demand_template = {
    "title": None,             # Novel title
    "genre": None,             # Genre type, e.g., Fantasy, Sci-Fi, Mystery, etc.
    "background": None,        # Story background (Worldview/Era/Location/Environment)
    "style": None,             # Target literary style, e.g., Serious, Light-hearted, etc.
    "character_count": None,   # Number of main characters
    "language_tone": None      # Language style, e.g., Ornate, Concise, Humorous, etc.
}

# Initialization information template
init_info_template = {
    "applied_template": None,      # The content of the demand template that was actually applied
    "config_items": {},            # Configuration items generated during initialization (e.g., chapters, structure)
    "characters": [],              # List of main characters, recommended as a list structure
    "operator": None,              # Name of the operator or Agent that performed the initialization
    "remark": None                 # Remarks or additional notes
}