"""Ad-group and ad tools: get_ad_groups and create_text_ad."""

from .client import (
    get_client,
    resolve_customer_id,
    handle_errors,
    is_readonly,
    readonly_response,
)


@handle_errors
def get_ad_groups(campaign_id: str, customer_id: str | None = None) -> list | dict:
    """List the ad groups under a campaign with status and default CPC bid.

    Args:
        campaign_id: The campaign's numeric ID.
        customer_id: 10-digit account ID. Optional if GOOGLE_ADS_CUSTOMER_ID is set.
    """
    client = get_client()
    cid = resolve_customer_id(customer_id)
    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT ad_group.id, ad_group.name, ad_group.status, ad_group.type,
               ad_group.cpc_bid_micros, campaign.id
        FROM ad_group
        WHERE campaign.id = {int(campaign_id)}
        ORDER BY ad_group.name
    """
    results = []
    for row in ga_service.search(customer_id=cid, query=query):
        results.append(
            {
                "id": str(row.ad_group.id),
                "name": row.ad_group.name,
                "status": row.ad_group.status.name,
                "type": row.ad_group.type_.name,
                "default_cpc_bid": round(row.ad_group.cpc_bid_micros / 1_000_000, 2),
            }
        )
    return results


@handle_errors
def create_text_ad(
    ad_group_id: str,
    headlines: list[str],
    descriptions: list[str],
    final_url: str,
    customer_id: str | None = None,
    paused: bool = True,
) -> dict:
    """Create a Responsive Search Ad (RSA) in an ad group.

    Google requires 3-15 headlines (max 30 chars each) and 2-4 descriptions
    (max 90 chars each). New ads default to PAUSED so a human can review first.

    Args:
        ad_group_id: The ad group's numeric ID.
        headlines: 3-15 headline strings.
        descriptions: 2-4 description strings.
        final_url: Landing page URL (e.g. https://example.com/offer).
        customer_id: 10-digit account ID. Optional if GOOGLE_ADS_CUSTOMER_ID is set.
        paused: Create the ad paused (default True). Set False to launch immediately.
    """
    if len(headlines) < 3:
        return {
            "error": "validation",
            "message": "Responsive Search Ads need at least 3 headlines (max 15).",
        }
    if len(descriptions) < 2:
        return {
            "error": "validation",
            "message": "Responsive Search Ads need at least 2 descriptions (max 4).",
        }

    cid = resolve_customer_id(customer_id)
    if is_readonly():
        return readonly_response(
            "create_text_ad",
            ad_group_id=ad_group_id,
            headlines=headlines,
            descriptions=descriptions,
            final_url=final_url,
            paused=paused,
        )

    client = get_client()
    ad_group_service = client.get_service("AdGroupService")
    ad_group_ad_service = client.get_service("AdGroupAdService")

    op = client.get_type("AdGroupAdOperation")
    ad_group_ad = op.create
    ad_group_ad.ad_group = ad_group_service.ad_group_path(cid, ad_group_id)
    ad_group_ad.status = (
        client.enums.AdGroupAdStatusEnum.PAUSED
        if paused
        else client.enums.AdGroupAdStatusEnum.ENABLED
    )

    ad = ad_group_ad.ad
    ad.final_urls.append(final_url)
    for text in headlines[:15]:
        asset = client.get_type("AdTextAsset")
        asset.text = text
        ad.responsive_search_ad.headlines.append(asset)
    for text in descriptions[:4]:
        asset = client.get_type("AdTextAsset")
        asset.text = text
        ad.responsive_search_ad.descriptions.append(asset)

    resp = ad_group_ad_service.mutate_ad_group_ads(customer_id=cid, operations=[op])
    return {
        "success": True,
        "status": "PAUSED" if paused else "ENABLED",
        "resource_name": resp.results[0].resource_name,
    }
