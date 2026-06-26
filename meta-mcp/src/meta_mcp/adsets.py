"""Ad-set tools: get_ad_sets (Meta's analogue of Google Ads' ad groups)."""

from .client import (
    get_client,
    resolve_account_id,
    act_path,
    handle_errors,
    minor_to_major,
)


@handle_errors
def get_ad_sets(campaign_id: str | None = None, account_id: str | None = None) -> list | dict:
    """List ad sets with status, budget, optimization goal and bid info.

    Args:
        campaign_id: Optional — restrict to one campaign. When omitted, lists all
            ad sets in the account.
        account_id: Ad-account id (digits or 'act_' form). Optional if
            META_AD_ACCOUNT_ID is set. Used when campaign_id is not given.
    """
    client = get_client()
    fields = (
        "id,name,status,effective_status,campaign_id,"
        "daily_budget,lifetime_budget,optimization_goal,billing_event,bid_amount"
    )
    if campaign_id:
        rows = client.get_all(f"{campaign_id}/adsets", {"fields": fields, "limit": 200})
    else:
        aid = act_path(resolve_account_id(account_id))
        rows = client.get_all(f"{aid}/adsets", {"fields": fields, "limit": 200})

    out = []
    for r in rows:
        out.append(
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "status": r.get("status"),
                "effective_status": r.get("effective_status"),
                "campaign_id": r.get("campaign_id"),
                "daily_budget": (
                    minor_to_major(r["daily_budget"]) if "daily_budget" in r else None
                ),
                "lifetime_budget": (
                    minor_to_major(r["lifetime_budget"]) if "lifetime_budget" in r else None
                ),
                "optimization_goal": r.get("optimization_goal"),
                "billing_event": r.get("billing_event"),
                "bid_amount": minor_to_major(r["bid_amount"]) if "bid_amount" in r else None,
            }
        )
    return out
