"""Ad tool: get_ads (the individual ads/creatives under an ad set).

Ad creation is intentionally NOT exposed in this version. Unlike a Google
Responsive Search Ad (just headlines + descriptions), a Meta ad requires a
creative tied to a Facebook Page, image/video asset hashes, and a call-to-action
spec — too much surface to do safely as a single MCP tool today. List + status
+ budget management is supported; build new Meta ads in Ads Manager for now.
"""

from .client import get_api, handle_errors


@handle_errors
def get_ads(ad_set_id: str) -> list | dict:
    """List the ads under an ad set with their status.

    Args:
        ad_set_id: The ad set's numeric ID (from get_ad_sets).
    """
    from facebook_business.adobjects.adset import AdSet
    from facebook_business.adobjects.ad import Ad

    api = get_api()
    adset = AdSet(ad_set_id, api=api)
    fields = [Ad.Field.id, Ad.Field.name, Ad.Field.status]
    results = []
    for x in adset.get_ads(fields=fields, params={"limit": 100}):
        results.append(
            {
                "id": x.get(Ad.Field.id),
                "name": x.get(Ad.Field.name),
                "status": x.get(Ad.Field.status),
            }
        )
    return results
