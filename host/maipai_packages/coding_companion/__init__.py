"""The coding companion: the robot shows what a coding agent on this computer is doing.

The agent posts a small status over a local, token-protected endpoint. The robot shows it with the ring
light and one soft tone, and says it aloud only on request, from a fixed phrase. Nothing here reaches
the model prompt or the chat history, the model gets no tools from this package, and nothing is sent
back to the agent (no approvals, no commands). Off by default; the socket is not opened while off.
"""

from maipai_packages.coding_companion.state import AgentStatus, shared_status

__all__ = ["AgentStatus", "shared_status"]
