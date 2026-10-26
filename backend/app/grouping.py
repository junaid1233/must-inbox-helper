"""Group processed messages by their single predicted intent."""

from collections.abc import Sequence

from app.models import INTENT_LABELS, Intent, IntentGroup, MessageResult


def group_results(results: Sequence[MessageResult]) -> list[IntentGroup]:
    """One group per intent that has messages, in Intent order; members keep input order."""
    members: dict[Intent, list[MessageResult]] = {intent: [] for intent in Intent}
    for result in results:
        members[result.intent].append(result)
    return [
        IntentGroup(
            intent=intent,
            label=INTENT_LABELS[intent],
            count=len(group),
            needs_attention_count=sum(r.needs_human_attention for r in group),
            message_ids=[r.message_id for r in group],
        )
        for intent, group in members.items()
        if group
    ]
