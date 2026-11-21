from google.adk.agents import SequentialAgent, LoopAgent, ParallelAgent
SequentialAgent(name="a", sub_agents=[])
LoopAgent(name="b", sub_agents=[])
ParallelAgent(name="c", sub_agents=[])
print("constructed all three under the default warning filter")
