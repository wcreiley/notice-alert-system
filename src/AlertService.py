import os
import requests
from dotenv import load_dotenv


class AlertService:

    def __init__(self):
        print("AlertService initialized")
        load_dotenv()
        self.api_host = os.environ.get("PATHWAY_REST_CONNECTOR_HOST", "127.0.0.1")
        self.api_port = int(os.environ.get("PATHWAY_REST_CONNECTOR_PORT", 8080))
        self.url = f"http://{self.api_host}:{self.api_port}/"

    def build_capacity_constraint_prompt(self):
        return """
            What are all the capacity constraints?
            Alert me of any new capacity constraints.
            
            Identify the notice type.
            Identify the location.
            Identify the pipeline segment.
            Identify the duration of the outage.
            Identify the change in capacity.
        """

    def build_site_capacity_constraint_prompt(self):
        return """
            What are the site names of any capacity constraints.
            Alert me of any new capacity constraints.
        """

    def build_creole_trail_prompt(self):
        return """
            Are there any outages for Creole Trail.
            Alert me of any outages.
        """

    def run(self):
        print("Setting up static alert prompts")

        active_prompts = [
            self.build_site_capacity_constraint_prompt(),
            self.build_capacity_constraint_prompt(),
            self.build_creole_trail_prompt()
        ]

        for prompt in active_prompts:
            data = {"query": prompt, "user": "user"}

            print(f"Prompt: {data}")
            response = requests.post(self.url, json=data)
            print(f"Response: {str(response.content)}")


if __name__ == "__main__":
    AlertService().run()
