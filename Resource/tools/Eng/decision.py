from autogen_agentchat.agents import AssistantAgent
from Resource.template.storygen_prompt.decision import decision_prompt_template
from Resource.tools.extract_llm_content import extract_llm_content
from Resource.tools.strip_markdown_codeblock import strip_markdown_codeblock
from autogen_agentchat.messages import TextMessage
import json
import asyncio


async def score_plan(plan, model_client):
    """
    Score a single plan.

    This function defines multiple evaluation dimensions and their weights,
    uses a scoring agent to analyze the plan, extracts atomic logic scores,
    and computes a weighted overall score.

    Args:
        plan (str): The plan content to be scored.
        model_client: The model client instance used to interact with the scoring agent.

    Returns:
        float: The weighted composite score.
    """
    # Define weights for each evaluation dimension. TODO: weights can be adjusted
    weights = {
        "p1": 0.1,   # Consistency with character motivation and background
        "p2": 0.15,  # Contribution to main story progression
        "p3": 0.1,   # Originality of the goal
        "p4": 0.15,  # Effectiveness in introducing conflict
        "p5": 0.1,   # Emotional resonance
        "p6": 0.1,   # Feasibility of the plan
        "p7": 0.1,   # Alignment between plan and characters
        "p8": 0.05,  # Multi-character interaction in the plan
        "p9": 0.1,   # Suspense and risk level
        "p10": 0.05  # Coherence and narrative appeal
    }

    # Define scoring agent to evaluate the plan
    # TODO: Scoring criteria need refinement
    score_agent = AssistantAgent(
        name="scoreAgent",
        description="Extract logical atoms from the plan and score each according to the template",
        model_client=model_client,
        system_message=decision_prompt_template
    )

    # Request score agent to analyze the plan
    # During debugging, using TextMessage to package input
    score_output = await score_agent.run(
        task=TextMessage(content=f"Please score the following plan according to the template:\n\n{plan}", source="user")
    )
    await score_agent.model_context.clear()

    print("Logical atoms scoring result:")
    print(score_output)

    # Extract and parse LLM output
    score_atoms_output = extract_llm_content(score_output)
    score_atoms_json = strip_markdown_codeblock(score_atoms_output)
    try:
        score_atoms = json.loads(score_atoms_json)
    except json.JSONDecodeError as e:
        print(f"Failed to parse score atoms JSON: {e}")
        # Fallback: return zero score if parsing fails
        return 0.0

    print(f"score_atoms: {score_atoms}")

    # Compute weighted composite score
    weighted_score = 0.0
    for key, value in score_atoms.items():
        if key in weights:
            weighted_score += value * weights[key]

    return weighted_score


async def evaluate_plan(plans, model_client):
    """
    Evaluate a list of plans, score each, and select the highest-scoring one.

    Args:
        plans (list): List of plans, each being a dictionary.
        model_client: Model client instance used for scoring.

    Returns:
        tuple: The best plan and its score (best_plan, best_score).
    """
    plan_scores = []
    for plan in plans:
        # Score each story plan
        score = await score_plan(plan, model_client)
        # Append plan and its score
        plan_scores.append((plan, score))

    # Select the plan with the highest score
    if plan_scores:  # Ensure list is not empty
        best_plan, best_score = max(plan_scores, key=lambda x: x[1])
    else:
        best_plan, best_score = None, 0.0

    # Return the best plan and its score
    return best_plan, best_score