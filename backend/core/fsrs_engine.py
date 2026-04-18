"""
FSRS engine wrapper.
Handles Card ↔ DB row serialization and review_card operations.
Uses py-fsrs (FSRS-6, 21 parameters).
"""
from datetime import datetime, timezone
from fsrs import Scheduler, Card, Rating, State, ReviewLog


# Map integer ratings to py-fsrs Rating enum
RATING_MAP = {
    1: Rating.Again,
    2: Rating.Hard,
    3: Rating.Good,
    4: Rating.Easy,
}

# Map py-fsrs State enum to labels
STATE_LABELS = {
    State.Learning: "Learning",
    State.Review: "Review",
    State.Relearning: "Relearning",
}


def create_new_card() -> Card:
    """Create a new FSRS card with default state (due=NOW, state=Learning)."""
    return Card()


def card_to_db_dict(card: Card) -> dict:
    """
    Convert a py-fsrs Card to a dict matching DB columns.
    Used when inserting or updating questions table.
    """
    return {
        "due": card.due,
        "stability": card.stability,
        "difficulty": card.difficulty,
        "step": card.step,
        "state": card.state.value if isinstance(card.state, State) else int(card.state),
        "last_review": card.last_review,
    }


def card_from_db_row(row: dict) -> Card:
    """
    Reconstruct a py-fsrs Card from a DB row (asyncpg Record or dict).
    """
    card = Card()
    card.due = row["due"]
    card.stability = row["stability"]
    card.difficulty = row["difficulty"]
    card.step = row["step"]
    card.state = State(row["state"])
    card.last_review = row["last_review"]
    return card


def review_card(scheduler: Scheduler, card: Card, rating: int) -> tuple[Card, ReviewLog]:
    """
    Apply a rating to a card and return updated card + review log.

    Args:
        scheduler: py-fsrs Scheduler instance
        card: Current card state (reconstructed from DB)
        rating: User rating 1-4 (Again/Hard/Good/Easy)

    Returns:
        Tuple of (updated_card, review_log)
    """
    fsrs_rating = RATING_MAP[rating]
    updated_card, review_log = scheduler.review_card(card, fsrs_rating)
    return updated_card, review_log


def get_scheduled_days(card: Card) -> float:
    """Calculate scheduled days from card state (due - last_review)."""
    if card.last_review and card.due:
        delta = card.due - card.last_review
        return delta.total_seconds() / 86400.0
    return 0.0


def get_state_label(state_value: int) -> str:
    """Get human-readable state label from state integer value."""
    try:
        state = State(state_value)
        return STATE_LABELS.get(state, "Learning")
    except ValueError:
        return "Learning"
