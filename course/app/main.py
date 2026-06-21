# Brings everything together for the command line interface

"""
Command Line Interface (CLI) for the AI FAQ Assistant.

This script brings together data ingestion, the search agent, and logging 
to provide an interactive terminal-based Q&A experience.
"""

import ingest
import search_agent
import logs
import asyncio

REPO_OWNER = "DataTalksClub"
REPO_NAME = "faq"

def initialize_index():
    """
    Initializes the data index by downloading and processing repository data.
    
    Returns:
        Index: A fitted search index containing the filtered repository data.
    """

    print(f"Starting AI FAQ Assistant for {REPO_OWNER}/{REPO_NAME}")
    print("Initializing data ingestion...")

    # Renamed from 'filter' to 'doc_filter' to avoid shadowing Python's built-in filter()
    def doc_filter(doc: dict) -> bool:
        return 'data-engineering' in doc['filename']

    # Updated the keyword argument to 'filter_func' to match ingest.py
    index = ingest.index_data(REPO_OWNER, REPO_NAME, filter_func=doc_filter)
    print("Data indexing completed successfully!")
    return index

def initialize_agent(index):
    """
    Initializes the Pydantic AI search agent using the provided index.
    
    Args:
        index: The fitted search index to be used by the agent.
        
    Returns:
        Agent: An initialized Pydantic AI agent ready to process prompts.
    """
    print("Initializing search agent...")
    agent = search_agent.init_agent(index, REPO_OWNER, REPO_NAME)
    print("Agent initialized successfully!")
    return agent

def main():
    """
    Main execution loop for the CLI application.
    Initializes resources and continuously prompts the user for questions 
    until they type 'stop'.
    """
    index = initialize_index()
    agent = initialize_agent(index)
    print("\nReady to answer your questions!")
    print("Type 'stop' to exit the program.\n")

    while True:
        question = input("Your question: ")
        if question.strip().lower() == 'stop':
            print("Exiting program. Goodbye!")
            break

        print("Processing your question...")
        response = asyncio.run(agent.run(user_prompt=question))
        # Log the interaction to file
        logs.log_interaction_to_file(agent, response.new_messages())

        print("\nResponse:\n", response.output)
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main()