"""Ad-set tool: get_ad_sets (the Meta analogue of get_ad_groups)."""

from .client import get_api, handle_errors, minor_to_units


@handle_errors
def get_ad_sets(campaign_id: str) -> list | dict:
    """List the ad sets under a campaign with status, budget, optimization goal and bid.

    A ``daily_budget`` / ``lifetime_budget`` of null means the budget is held at
    the campaign level (CBO) rather than on the ad set. ``bid_amount`` is in
    whole currency units (null when the ad set uses an automatic bid strategy).

    Args:
        campaign_id: The campaign's numeric ID (from get_campaigns).
    """
    from facebook_business.adobjects.campaign import Campaign
    from facebook_business.adobjects.adset import AdSet

    api = get_api()
    camp = Campaign(campaign_id, api=api)
    fields = [
        AdSet.Field.id,
        AdSet.Field.name,
        AdSet.Field.status,
        AdSet.Field.daily_budget,
        AdSet.Field.lifetime_budget,
        AdSet.Field.optimization_goal,
        AdSet.Field.bid_amount,
    ]
    results = []
    for a in camp.get_ad_sets(fields=fields, params={"limit": 100}):
        results.append(
            {
                "id": a.get(AdSet.Field.id),
                "name": a.get(AdSet.Field.name),
                "status": a.get(AdSet.Field.status),
                "optimization_goal": a.get(AdSet.Field.optimization_goal),
                "daily_budget": minor_to_units(a.get(AdSet.Field.daily_budget)),
                "lifetime_budget": minor_to_units(a.get(AdSet.Field.lifetime_budget)),
                "bid_amount": minor_to_units(a.get(AdSet.Field.bid_amount)),
            }
        )
    return results
