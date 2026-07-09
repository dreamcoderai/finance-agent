from agents.finance_agent import FinanceAgent


def main():

    agent = FinanceAgent()

    print("=" * 60)
    print("Finance AI Assistant")
    print("Type 'exit' to quit")
    print("Type 'clear' to clear conversation")
    print("=" * 60)

    while True:

        question = input("\nYou: ").strip()

        if question.lower() in ["exit", "quit"]:
            print("\nGoodbye!")
            break

        if question.lower() == "clear":
            agent.clear_history()
            print("\nConversation cleared.")
            continue

        try:
            answer = agent.ask(question)

            print("\nFinance AI:\n")
            print(answer)

        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()