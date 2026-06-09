"""Campaign-level tools: list, pause/enable, budget."""

from .client import (
    get_client,
    resolve_customer_id,
    handle_errors,
    is_readonly,
    readonly_response,
)

ENTITY_TYPES = {"campaign", "ad_group", "ad"}


@handle_errors
def get_campaigns(customer_id: str | None = None) -> list | dict:
    """List all campaigns with their status and daily budget.

    Args:
        customer_id: 10-digit account ID. Optional if GOOGLE_ADS_CUSTOMER_ID is set.
    """
    client = get_client()
    cid = resolve_customer_id(customer_id)
    ga_service = client.get_service("GoogleAdsService")
    query = """
        SELECT campaign.id, campaign.name, campaign.status,
               campaign.advertising_channel_type,
               campaign_budget.amount_micros
        FROM campaign
        ORDER BY campaign.name
    """
    results = []
    for row in ga_service.search(customer_id=cid, query=query):
        results.append(
            {
                "id": str(row.campaign.id),
                "name": row.campaign.name,
                "status": row.campaign.status.name,
                "channel_type": row.campaign.advertising_channel_type.name,
                "daily_budget": round(row.campaign_budget.amount_micros / 1_000_000, 2),
            }
        )
    return results


def _set_entity_status(client, cid: str, entity_type: str, entity_id: str, status_name: str):
    """Flip ENABLED/PAUSED on a campaign, ad group or ad. Returns the resource name."""
    from google.api_core import protobuf_helpers

    if entity_type == "campaign":
        service = client.get_service("CampaignService")
        op = client.get_type("CampaignOperation")
        entity = op.update
        entity.resource_name = service.campaign_path(cid, entity_id)
        entity.status = client.enums.CampaignStatusEnum[status_name]
        client.copy_from(op.update_mask, protobuf_helpers.field_mask(None, entity._pb))
        resp = service.mutate_campaigns(customer_id=cid, operations=[op])
    elif entity_type == "ad_group":
        service = client.get_service("AdGroupService")
        op = client.get_type("AdGroupOperation")
        entity = op.update
        entity.resource_name = service.ad_group_path(cid, entity_id)
        entity.status = client.enums.AdGroupStatusEnum[status_name]
        client.copy_from(op.update_mask, protobuf_helpers.field_mask(None, entity._pb))
        resp = service.mutate_ad_groups(customer_id=cid, operations=[op])
    else:  # ad — needs both the ad group id and ad id as "<ad_group_id>~<ad_id>"
        if "~" not in str(entity_id):
            raise ValueError(
                "For an ad, entity_id must be '<ad_group_id>~<ad_id>' "
                "(get these from get_performance at level='ad')."
            )
        ad_group_id, ad_id = str(entity_id).split("~", 1)
        service = client.get_service("AdGroupAdService")
        op = client.get_type("AdGroupAdOperation")
        entity = op.update
        entity.resource_name = service.ad_group_ad_path(cid, ad_group_id, ad_id)
        entity.status = client.enums.AdGroupAdStatusEnum[status_name]
        client.copy_from(op.update_mask, protobuf_helpers.field_mask(None, entity._pb))
        resp = service.mutate_ad_group_ads(customer_id=cid, operations=[op])

    return resp.results[0].resource_name


@handle_errors
def pause_entity(
    entity_type: str,
    entity_id: str,
    customer_id: str | None = None,
) -> dict:
    """Pause a campaign, ad group, or ad.

    Args:
        entity_type: "campaign", "ad_group", or "ad".
        entity_id: The entity's numeric ID. For an ad, pass "<ad_group_id>~<ad_id>".
        customer_id: 10-digit account ID. Optional if GOOGLE_ADS_CUSTOMER_ID is set.
    """
    if entity_type not in ENTITY_TYPES:
        return {"error": "invalid_entity_type", "allowed": sorted(ENTITY_TYPES)}
    cid = resolve_customer_id(customer_id)
    if is_readonly():
        return readonly_response("pause_entity", entity_type=entity_type, entity_id=entity_id)
    client = get_client()
    resource = _set_entity_status(client, cid, entity_type, entity_id, "PAUSED")
    return {"success": True, "status": "PAUSED", "resource_name": resource}


@handle_errors
def enable_entity(
    entity_type: str,
    entity_id: str,
    customer_id: str | None = None,
) -> dict:
    """Enable (un-pause) a campaign, ad group, or ad.

    Args:
        entity_type: "campaign", "ad_group", or "ad".
        entity_id: The entity's numeric ID. For an ad, pass "<ad_group_id>~<ad_id>".
        customer_id: 10-digit account ID. Optional if GOOGLE_ADS_CUSTOMER_ID is set.
    """
    if entity_type not in ENTITY_TYPES:
        return {"error": "invalid_entity_type", "allowed": sorted(ENTITY_TYPES)}
    cid = resolve_customer_id(customer_id)
    if is_readonly():
        return readonly_response("enable_entity", entity_type=entity_type, entity_id=entity_id)
    client = get_client()
    resource = _set_entity_status(client, cid, entity_type, entity_id, "ENABLED")
    return {"success": True, "status": "ENABLED", "resource_name": resource}


@handle_errors
def update_budget(
    campaign_id: str,
    daily_budget: float,
    customer_id: str | None = None,
) -> dict:
    """Update a campaign's daily budget (in the account's currency, e.g. 500 = 500 DKK/day).

    Args:
        campaign_id: The campaign's numeric ID.
        daily_budget: New daily budget amount in whole currency units.
        customer_id: 10-digit account ID. Optional if GOOGLE_ADS_CUSTOMER_ID is set.
    """
    cid = resolve_customer_id(customer_id)
    if is_readonly():
        return readonly_response(
            "update_budget", campaign_id=campaign_id, new_daily_budget=daily_budget
        )

    client = get_client()
    ga_service = client.get_service("GoogleAdsService")

    # Find the budget resource attached to this campaign.
    query = f"""
        SELECT campaign.id, campaign.name, campaign_budget.resource_name
        FROM campaign
        WHERE campaign.id = {int(campaign_id)}
    """
    rows = list(ga_service.search(customer_id=cid, query=query))
    if not rows:
        return {"error": "campaign_not_found", "message": f"No campaign with id {campaign_id}."}

    budget_resource = rows[0].campaign_budget.resource_name

    from google.api_core import protobuf_helpers

    budget_service = client.get_service("CampaignBudgetService")
    op = client.get_type("CampaignBudgetOperation")
    budget = op.update
    budget.resource_name = budget_resource
    budget.amount_micros = int(round(float(daily_budget) * 1_000_000))
    client.copy_from(op.update_mask, protobuf_helpers.field_mask(None, budget._pb))
    resp = budget_service.mutate_campaign_budgets(customer_id=cid, operations=[op])

    return {
        "success": True,
        "campaign_id": str(campaign_id),
        "campaign": rows[0].campaign.name,
        "new_daily_budget": float(daily_budget),
        "resource_name": resp.results[0].resource_name,
    }
