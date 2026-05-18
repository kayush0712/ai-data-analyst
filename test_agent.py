import pandas as pd

from agent.tool_agent import run_agent

# Load sample dataset
df = pd.read_csv(
    "employee_performance_data.csv"
)

# Test question
question = (
    "clean this dataset, generate chart visualization and export csv"
)

# Run agent
result = run_agent(
    question,
    df
)

print("\nFINAL RESULT:")
print(result)