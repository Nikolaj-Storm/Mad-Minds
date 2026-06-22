"""Campaign listing + the cross-entity write tools (pause / enable / budget).

Meta's hierarchy is campaign -> ad set -> ad. Status changes apply to any of
the three; budgets apply to a campaign (CBO) or an ad set. All writes respect
READONLY_MODE and are additionally gated by the /ad-actions spend-gate in Mad
Minds.
"""

from .client import (
    get_api,
    resolve_account_id,
    handle_errors,
    is_readonly,
    readonly_response,
    minor_to_units,
    units_to_minor,
)

ENTITY_TYPES = {"campaign", "adset", "ad"}
BUDGET_ENTITY_TYPES = {"campaign", "adset"}


def _entity(api, entity_type: str, entity_id: str):
    """Return the SDK ad object for ``entity_type`` bound to this request's api."""
    from facebook_business.adobjects.campaign import Campaign
    from facebook_business.adobjects.adset import AdSet
    from facebook_business.adobjects.ad import Ad

    cls = {"campaign": Campaign, "adset": AdSet, "ad": Ad}[entity_type]
    return cls(entity_id, api=api)


@handle_errors
def get_campaigns(account_id: str | None = None) -> list | dict:
    """List all campaigns in an ad account with status, objective and budget.

    A ``daily_budget`` / ``lifetime_budget`` of null means this campaign has no
    campaign-level budget — the budget lives on its ad sets instead.

    Args:
        account_id: The ad account ID ("act_…" or just its digits). Optional if
            META_AD_ACCOUNT_ID is set.
    """
    from facebook_business.adobjects.adaccount import AdAccount
    from facebook_business.adobjects.campaign import Campaign

    api = get_api()
    acct = AdAccount(resolve_account_id(account_id), api=api)
    fields = [
        Campaign.Field.id,
        Campaign.Field.name,
        Campaign.Field.status,
        Campaign.Field.objective,
        Campaign.Field.daily_budget,
        Campaign.Field.lifetime_budget,
    ]
    results = []
    for c in acct.get_campaigns(fields=fields, params={"limit": 100}):
        results.append(
            {
                "id": c.get(Campaign.Field.id),
                "name": c.get(Campaign.Field.name),
                "status": c.get(Campaign.Field.status),
                "objective": c.get(Campaign.Field.objective),
                "daily_budget": minor_to_units(c.get(Campaign.Field.daily_budget)),
                "lifetime_budget": minor_to_units(c.get(Campaign.Field.lifetime_budget)),
            }
        )
    return results


def _set_status(entity_type: str, entity_id: str, status: str) -> dict:
    if entity_type not in ENTITY_TYPES:
        return {"error": "invalid_entity_type", "allowed": sorted(ENTITY_TYPES)}
    api = get_api()
    obj = _entity(api, entity_type, entity_id)
    obj.api_update(params={"status": status})
    return {
        "success": True,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "status": status,
    }


@handle_errors
def pause_entity(entity_type: str, entity_id: str) -> dict:
    """Pause a campaign, ad set, or ad (sets its status to PAUSED).

    Args:
        entity_type: "campaign", "adset", or "ad".
        entity_id: The entity's numeric ID (from get_campaigns / get_ad_sets / get_ads).
    """
    if entity_type not in ENTITY_TYPES:
        return {"error": "invalid_entity_type", "allowed": sorted(ENTITY_TYPES)}
    if is_readonly():
        return readonly_response("pause_entity", entity_type=entity_type, entity_id=entity_id)
    return _set_status(entity_type, entity_id, "PAUSED")


@handle_errors
def enable_entity(entity_type: str, entity_id: str) -> dict:
    """Enable (un-pause) a campaign, ad set, or ad (sets its status to ACTIVE).

    Args:
        entity_type: "campaign", "adset", or "ad".
        entity_id: The entity's numeric ID (from get_campaigns / get_ad_sets / get_ads).
    """
    if entity_type not in ENTITY_TYPES:
        return {"error": "invalid_entity_type", "allowed": sorted(ENTITY_TYPES)}
    if is_readonly():
        return readonly_response("enable_entity", entity_type=entity_type, entity_id=entity_id)
    return _set_status(entity_type, entity_id, "ACTIVE")


@handle_errors
def update_budget(
    entity_type: str,
    entity_id: str,
    daily_budget: float | None = None,
    lifetime_budget: float | None = None,
) -> dict:
    """Update a campaign's or ad set's budget (in whole currency units, e.g. 500 = 500 DKK).

    Set the budget on whichever level actually carries it: a CBO campaign holds
    the budget at the campaign level, otherwise each ad set holds its own. Pass
    exactly ONE of daily_budget or lifetime_budget.

    Args:
        entity_type: "campaign" or "adset" (ads have no budget).
        entity_id: The entity's numeric ID.
        daily_budget: New daily budget in whole currency units. Mutually exclusive with lifetime_budget.
        lifetime_budget: New lifetime budget in whole currency units. Mutually exclusive with daily_budget.
    """
    if entity_type not in BUDGET_ENTITY_TYPES:
        return {
            "error": "invalid_entity_type",
            "message": "Budgets are set on a 'campaign' or an 'adset'.",
            "allowed": sorted(BUDGET_ENTITY_TYPES),
        }
    if (daily_budget is None) == (lifetime_budget is None):
        return {
            "error": "invalid_input",
            "message": "Provide exactly one of daily_budget or lifetime_budget (whole currency units).",
        }

    if is_readonly():
        return readonly_response(
            "update_budget",
            entity_type=entity_type,
            entity_id=entity_id,
            daily_budget=daily_budget,
            lifetime_budget=lifetime_budget,
        )

    api = get_api()
    if daily_budget is not None:
        params = {"daily_budget": units_to_minor(daily_budget)}
        changed = {"new_daily_budget": float(daily_budget)}
    else:
        params = {"lifetime_budget": units_to_minor(lifetime_budget)}
        changed = {"new_lifetime_budget": float(lifetime_budget)}

    obj = _entity(api, entity_type, entity_id)
    obj.api_update(params=params)
    return {"success": True, "entity_type": entity_type, "entity_id": str(entity_id), **changed}
