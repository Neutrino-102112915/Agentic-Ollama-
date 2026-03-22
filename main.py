#!/usr/bin/env python3
import json
import subprocess
import sys
import os
import datetime
import time

AGENTS_FILE = "agents.json"
WORKSPACES_FILE = "workspaces.json"
OLLAMA_CMD = "ollama"
DEFAULT_SYSTEM_PROMPT = "You are a helpful AI agent. Respond clearly and concisely."


# -----------------------------
# Utility: colors
# -----------------------------
def color(num, text):
    return f"\033[38;5;{num}m{text}\033[0m"


# -----------------------------
# Agent manager
# -----------------------------
class Agent:
    def __init__(self, name, model, description, system_prompt=None):
        self.name = name
        self.model = model
        self.description = description
        self.system_prompt = f"{system_prompt or DEFAULT_SYSTEM_PROMPT} | {DEFAULT_SYSTEM_PROMPT}"

    @staticmethod
    def load_agents():
        if not os.path.exists(AGENTS_FILE):
            return []
        try:
            with open(AGENTS_FILE, "r") as f:
                content = f.read().strip()
                if not content:
                    return []
                return [Agent(**a) for a in json.loads(content)]
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    @staticmethod
    def find(name):
        for a in Agent.load_agents():
            if a.name == name:
                return a
        return None

    @staticmethod
    def list_agents():
        agents = Agent.load_agents()
        if not agents:
            print("No agents found.")
            return
        for a in agents:
            print(f"- {a.name} ({a.model})")

    @staticmethod
    def create(name, model, description, system_prompt=None):
        agents = Agent.load_agents()
        agents.append(Agent(name, model, description, system_prompt))
        data = [
            {
                "name": a.name,
                "model": a.model,
                "description": a.description,
                "system_prompt": a.system_prompt,
            }
            for a in agents
        ]
        with open(AGENTS_FILE, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Agent '{name}' created.")


# -----------------------------
# Workspace manager
# -----------------------------
class Workspace:
    def __init__(self, name, agents=None, model=None):
        self.name = name
        self.agents = agents or []  # list of agent names
        self.model = model or "default-model"

    @staticmethod
    def load_workspaces():
        if not os.path.exists(WORKSPACES_FILE):
            return []
        try:
            with open(WORKSPACES_FILE, "r") as f:
                content = f.read().strip()
                if not content:
                    return []
                return [Workspace(**w) for w in json.loads(content)]
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    @staticmethod
    def find(name):
        for w in Workspace.load_workspaces():
            if w.name == name:
                return w
        return None

    @staticmethod
    def list_workspaces():
        workspaces = Workspace.load_workspaces()
        if not workspaces:
            print("No workspaces found.")
            return
        for w in workspaces:
            print(f"- {w.name} (agents: {', '.join(w.agents)})")

    @staticmethod
    def create(name, agents, model=None):
        workspaces = Workspace.load_workspaces()
        workspaces.append(Workspace(name, agents, model))
        data = [
            {"name": w.name, "agents": w.agents, "model": w.model} for w in workspaces
        ]
        with open(WORKSPACES_FILE, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Workspace '{name}' created with agents: {', '.join(agents)}")


# -----------------------------
# Conversation tub
# -----------------------------
class Tub:
    def __init__(self, agent: Agent):
        self.agent = agent
        self.history = []

    def add_message(self, role, content):
        self.history.append({"role": role, "content": content})

    def build_prompt(self, user_input=None):
        prompt = f"SYSTEM: {self.agent.system_prompt}\n"
        for entry in self.history:
            prompt += f"{entry['role'].upper()}: {entry['content']}\n"
        if user_input:
            prompt += f"USER: {user_input}\n"
        prompt += "ASSISTANT:"
        return prompt

    def run(self, user_input):
        prompt = self.build_prompt(user_input)
        try:
            result = subprocess.run(
                [OLLAMA_CMD, "run", self.agent.model, prompt],
                capture_output=True,
                text=True,
                check=True,
            )
            output = result.stdout.strip()
            self.add_message("assistant", output)
            return output
        except subprocess.CalledProcessError as e:
            return f"Error: {e.stderr}"


# -----------------------------
# Single-agent chat
# -----------------------------
def interactive_chat(agent_name):
    os.system('cls' if os.name == 'nt' else 'clear')
    agent = Agent.find(agent_name)
    if not agent:
        print(f"Agent '{agent_name}' not found.")
        return

    tub = Tub(agent)
    print(f"Starting chat with agent '{agent_name}'. Type 'exit' to quit.\n")

    while True:
        try:
            now = datetime.datetime.now()
            user_input = input(f"{color(75, 'You')} {color(8, f'({now.strftime('%Y-%d-%m %H:%M:%S')})')} \n").strip()
            print('')
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting chat.")
                break
            response = tub.run(user_input)
            print(f"{color(208, agent_name)}\n{response}\n")
        except KeyboardInterrupt:
            print("\nExiting chat.")
            break


# -----------------------------
# Workspace multi-agent chat
# -----------------------------
def workspace_chat(workspace_name, turns=5, delay=1, message=''):
    workspace = Workspace.find(workspace_name)
    if not workspace:
        print(f"Workspace '{workspace_name}' not found.")
        return

    agents = [Agent.find(name) for name in workspace.agents]
    if any(a is None for a in agents):
        print("One or more agents in the workspace were not found.")
        return

    tubs = [Tub(agent) for agent in agents]

    now = datetime.datetime.now()
    if message:
        print(f"{color(75, 'You')}\n{message}\n")
    else:
        message = input(f'{color(75, "You")}\n')
    tubs[0].add_message("user", message)

    for i in range(turns):
        for idx, tub in enumerate(tubs):
            reply = tub.run(message)
            now = datetime.datetime.now()
            print(f"{color(208, tub.agent.name)} {color(8, f'({now.strftime('%Y-%d-%m %H:%M:%S')})')}\n {reply}\n")

            next_tub = tubs[(idx + 1) % len(tubs)]
            next_tub.add_message("user", reply)
            message = reply
            time.sleep(delay)


# -----------------------------
# CLI entrypoint
# -----------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print(" python main.py <agent_name>            # single-agent chat")
        print(" python main.py --list                  # list agents")
        print(" python main.py --create                # create agent")
        print(" python main.py --workspace-list        # list workspaces")
        print(" python main.py --workspace-create      # create workspace")
        print(" python main.py --chat <workspace_name> # multi-agent workspace chat")
        return

    cmd = sys.argv[1]

    if cmd in ["--list", "-l"]:
        Agent.list_agents()
    elif cmd in ["--create", "-c"]:
        name = input("Name: ")
        model = input("Model: ")
        description = input("Description: ")
        system_prompt = input("System prompt (optional): ")
        Agent.create(name, model, description, system_prompt)
    elif cmd == "--workspace-list":
        Workspace.list_workspaces()
    elif cmd == "--workspace-create":
        name = input("Workspace name: ")
        agents = input("Agents (comma-separated): ").strip().split(",")
        model = input("Default model (optional): ").strip() or None
        Workspace.create(name, [a.strip() for a in agents], model)
    elif cmd == "--chat":
        if len(sys.argv) == 3:
            workspace_chat(sys.argv[2])
        else:
            print("Usage: python main.py --chat <workspace_name>")
    else:
        agent_name = cmd
        interactive_chat(agent_name)


if __name__ == "__main__":
    main()
