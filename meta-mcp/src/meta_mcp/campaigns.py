"""Campaign-level tools: list, pause/enable, budget.

Meta status model: campaigns/ad sets/ads use ``status`` ACTIVE | PAUSED (plus
read-only states like ARCHIVED/DELETED). Writes flip ACTIVE/PAUSED, mirroring the
Google Ads ENABLED/PAUSED tools. Budgets are minor currency units in the API;
``update_budget`` accepts whole currency units and converts.
"""

from .client import (
    get_client,
    resolve_account_id,
    act_path,
    handle_errors,
    is_readonly,
    readonly_response,
    minor_to_major,
    major_to_minor,
)

# Meta object levels a status flip can target. "adset" is Meta's spelling.
ENTITY_TYPES = {"campaign", "adset", "ad"}

# Map our READONLY/standard status words to Meta's effective_status -> status.
_ACTIVE = "ACTIVE"
_PAUSED = "PAUSED"


@handle_errors
def get_campaigns(account_id: str | None = None) -> list | dict:
    """List campaigns with status, objective and budget.

    Args:
        account_id: Ad-account id (digits or 'act_' form). Optional if
            META_AD_ACCOUNT_ID is set.
    """
    client = get_client()
    aid = act_path(resolve_account_id(account_id))
    fields = (
        "id,name,status,effective_status,objective,"
        "daily_budget,lifetime_budget,bid_strategy"
    )
    rows = client.get_all(f"{aid}/campaigns", {"fields": fields, "limit": 200})
    out = []
    for r in rows:
        # A campaign carries a budget only under Campaign Budget Optimization;
        # otherwise the budget lives on the ad sets.
        has_daily = "daily_budget" in r
        out.append(
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "status": r.get("status"),
                "effective_status": r.get("effective_status"),
                "objective": r.get("objective"),
                "budget_level": "campaign" if (has_daily or "lifetime_budget" in r) else "adset",
                "daily_budget": minor_to_major(r["daily_budget"]) if has_daily else None,
                "lifetime_budget": (
                    minor_to_major(r["lifetime_budget"]) if "lifetime_budget" in r else None
                ),
                "bid_strategy": r.get("bid_strategy"),
            }
        )
    return out


def _set_status(client, entity_type: str, entity_id: str, status: str) -> str:
    """POST a status change to a campaign/adset/ad node. Returns the entity id."""
    resp = client.post(str(entity_id), {"status": status})
    # Meta returns {"success": true} for node updates; echo the id back.
    if isinstance(resp, dict) and resp.get("success") is False:
        raise ValueError(f"Meta rejected the {entity_type} status change.")
    return str(entity_id)


@handle_errors
def pause_entity(entity_type: str, entity_id: str) -> dict:
    """Pause a campaign, ad set, or ad.

    Args:
        entity_type: "campaign", "adset", or "ad".
        entity_id: The entity's numeric node ID (from get_campaigns /
            get_ad_sets / get_ads). Meta IDs are globally unique, so no
            account_id is needed.
    """
    if entity_type not in ENTITY_TYPES:
        return {"error": "invalid_entity_type", "allowed": sorted(ENTITY_TYPES)}
    if is_readonly():
        return readonly_response("pause_entity", entity_type=entity_type, entity_id=entity_id)
    client = get_client()
    _set_status(client, entity_type, entity_id, _PAUSED)
    return {"success": True, "status": _PAUSED, "entity_type": entity_type, "id": str(entity_id)}


@handle_errors
def enable_entity(entity_type: str, entity_id: str) -> dict:
    """Enable (un-pause) a campaign, ad set, or ad.

    Args:
        entity_type: "campaign", "adset", or "ad".
        entity_id: The entity's numeric node ID.
    """
    if entity_type not in ENTITY_TYPES:
        return {"error": "invalid_entity_type", "allowed": sorted(ENTITY_TYPES)}
    if is_readonly():
        return readonly_response("enable_entity", entity_type=entity_type, entity_id=entity_id)
    client = get_client()
    _set_status(client, entity_type, entity_id, _ACTIVE)
    return {"success": True, "status": _ACTIVE, "entity_type": entity_type, "id": str(entity_id)}


@handle_errors
def update_budget(
    entity_id: str,
    daily_budget: float | None = None,
    lifetime_budget: float | None = None,
    entity_type: str = "campaign",
) -> dict:
    """Update a campaign's or ad set's budget (in whole currency units, e.g. 500 = 500 DKK).

    Unlike Google Ads (budget always at campaign level), Meta holds the budget on
    EITHER the campaign (Campaign Budget Optimization) OR the ad set. Point this at
    whichever node actually owns the budget — check get_campaigns' "budget_level".

    Args:
        entity_id: The campaign or ad set node ID that owns the budget.
        daily_budget: New daily budget in whole currency units. Provide this OR
            lifetime_budget, not both.
        lifetime_budget: New lifetime budget in whole currency units.
        entity_type: "campaign" or "adset" — which node entity_id refers to
            (used only for clearer messages; the node ID is authoritative).
    """
    if (daily_budget is None) == (lifetime_budget is None):
        return {
            "error": "validation",
            "message": "Provide exactly one of daily_budget or lifetime_budget.",
        }
    field = "daily_budget" if daily_budget is not None else "lifetime_budget"
    amount = daily_budget if daily_budget is not None else lifetime_budget

    if is_readonly():
        return readonly_response(
            "update_budget", entity_type=entity_type, entity_id=entity_id, **{f"new_{field}": amount}
        )

    client = get_client()
    client.post(str(entity_id), {field: major_to_minor(amount)})
    return {
        "success": True,
        "entity_type": entity_type,
        "id": str(entity_id),
        f"new_{field}": float(amount),
    }
