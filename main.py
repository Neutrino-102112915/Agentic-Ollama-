import json
import subprocess
import sys
import os
import datetime

AGENTS_FILE = "agents.json"
OLLAMA_CMD = "ollama"
DEFAULT_SYSTEM_PROMPT = "You are a helpful AI agent. Respond clearly and concisely."

class Agent:
    def __init__(self, name, model, description, system_prompt=None):
        self.name = name
        self.model = model
        self.description = description
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    @staticmethod
    def load_agents():
        try:
            with open(AGENTS_FILE, "r") as f:
                data = json.load(f)
                return [Agent(**a) for a in data]
        except FileNotFoundError:
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
            user_input = input(f"{color(75, "You")} {color(8, f"({now.strftime("%Y-%d-%m")})")} \n").strip()
            print('')
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting chat.")
                break
            response = tub.run(user_input)
            print(f"{color(208, agent_name)}\n{response}\n")
        except KeyboardInterrupt:
            print("\nExiting chat.")
            break

def color(num, text):
    return f"\033[38;5;{num}m{text}\033[0m"

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <agent_name>")
        print("Or: python main.py --list to list agents")
        print("Or: python main.py --create to create a new agent")
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
    else:
        # Assume the argument is an agent name and start chat
        agent_name = cmd
        interactive_chat(agent_name)


if __name__ == "__main__":
    main()
