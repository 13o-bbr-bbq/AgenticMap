"""Static audit for Amazon Bedrock AgentCore and legacy Bedrock Agents.

Checks are declared in `checks.yaml`; each module (`guardrail`, `action_group`,
`memory`, `gateway`, `identity`, `network`, `observability`) implements the
boto3-side query and Finding emission for its category.
"""
