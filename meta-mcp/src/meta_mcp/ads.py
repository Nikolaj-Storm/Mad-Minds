"""Ad tools: get_ads (read-only listing of the ads under an ad set or account).

NOTE on scope: Google Ads' module also offers create_text_ad. Creating a Meta ad
requires assembling a creative (object_story_spec / page-backed creative + image
or video assets), which is materially more involved and out of scope for this
read+manage server. Ad creation stays in the /ad-actions plugin workflow.
"""

from .client import (
    get_client,
    resolve_account_id,
    act_path,
    handle_errors,
)


@handle_errors
def get_ads(adset_id: str | None = None, account_id: str | None = None) -> list | dict:
    """List ads with status and their linked creative id.

    Args:
        adset_id: Optional — restrict to one ad set. When omitted, lists all ads
            in the account.
        account_id: Ad-account id (digits or 'act_' form). Optional if
            META_AD_ACCOUNT_ID is set. Used when adset_id is not given.
    """
    client = get_client()
    fields = "id,name,status,effective_status,adset_id,campaign_id,creative{id,name}"
    if adset_id:
        rows = client.get_all(f"{adset_id}/ads", {"fields": fields, "limit": 200})
    else:
        aid = act_path(resolve_account_id(account_id))
        rows = client.get_all(f"{aid}/ads", {"fields": fields, "limit": 200})

    out = []
    for r in rows:
        creative = r.get("creative") or {}
        out.append(
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "status": r.get("status"),
                "effective_status": r.get("effective_status"),
                "adset_id": r.get("adset_id"),
                "campaign_id": r.get("campaign_id"),
                "creative_id": creative.get("id"),
                "creative_name": creative.get("name"),
            }
        )
    return out
