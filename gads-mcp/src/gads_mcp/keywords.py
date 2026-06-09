"""Keyword tools: get_keywords and update_keyword_bid."""

from .client import (
    get_client,
    resolve_customer_id,
    handle_errors,
    is_readonly,
    readonly_response,
)


@handle_errors
def get_keywords(ad_group_id: str, customer_id: str | None = None) -> list | dict:
    """List the keywords in an ad group with match type, Quality Score and bid.

    Args:
        ad_group_id: The ad group's numeric ID.
        customer_id: 10-digit account ID. Optional if GOOGLE_ADS_CUSTOMER_ID is set.
    """
    client = get_client()
    cid = resolve_customer_id(customer_id)
    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT ad_group.id, ad_group_criterion.criterion_id,
               ad_group_criterion.keyword.text,
               ad_group_criterion.keyword.match_type,
               ad_group_criterion.status,
               ad_group_criterion.cpc_bid_micros,
               ad_group_criterion.quality_info.quality_score
        FROM keyword_view
        WHERE ad_group.id = {int(ad_group_id)}
        ORDER BY ad_group_criterion.keyword.text
    """
    results = []
    for row in ga_service.search(customer_id=cid, query=query):
        crit = row.ad_group_criterion
        results.append(
            {
                "criterion_id": str(crit.criterion_id),
                "keyword": crit.keyword.text,
                "match_type": crit.keyword.match_type.name,
                "status": crit.status.name,
                "quality_score": crit.quality_info.quality_score or None,
                "max_cpc": round(crit.cpc_bid_micros / 1_000_000, 2),
            }
        )
    return results


@handle_errors
def update_keyword_bid(
    ad_group_id: str,
    criterion_id: str,
    cpc_bid: float,
    customer_id: str | None = None,
) -> dict:
    """Update the max CPC bid on a single keyword.

    Args:
        ad_group_id: The ad group's numeric ID.
        criterion_id: The keyword's criterion ID (from get_keywords).
        cpc_bid: New max CPC in whole currency units (e.g. 4.50).
        customer_id: 10-digit account ID. Optional if GOOGLE_ADS_CUSTOMER_ID is set.
    """
    cid = resolve_customer_id(customer_id)
    if is_readonly():
        return readonly_response(
            "update_keyword_bid",
            ad_group_id=ad_group_id,
            criterion_id=criterion_id,
            new_max_cpc=cpc_bid,
        )

    client = get_client()
    from google.api_core import protobuf_helpers

    service = client.get_service("AdGroupCriterionService")
    op = client.get_type("AdGroupCriterionOperation")
    criterion = op.update
    criterion.resource_name = service.ad_group_criterion_path(cid, ad_group_id, criterion_id)
    criterion.cpc_bid_micros = int(round(float(cpc_bid) * 1_000_000))
    client.copy_from(op.update_mask, protobuf_helpers.field_mask(None, criterion._pb))
    resp = service.mutate_ad_group_criteria(customer_id=cid, operations=[op])

    return {
        "success": True,
        "criterion_id": str(criterion_id),
        "new_max_cpc": float(cpc_bid),
        "resource_name": resp.results[0].resource_name,
    }
