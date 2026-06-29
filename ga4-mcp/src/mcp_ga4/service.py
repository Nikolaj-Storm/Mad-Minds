"""Build Google Analytics API clients from a per-user OAuth access token.

The signed-in marketer's access token comes from FastMCP's GoogleProvider (the
server runs the OAuth flow; tokens persist in CLIENT_STORAGE_DIR=/data). Inside a
tool we read it with ``get_access_token().token`` and wrap it in google-auth
``Credentials`` so the Analytics client libraries can call the API as that user.

Two APIs:
  * Analytics Data API  (``google-analytics-data``)  — runs reports.
  * Analytics Admin API (``google-analytics-admin``) — lists accessible properties.
"""


def _credentials(access_token: str):
    from google.oauth2.credentials import Credentials
    return Credentials(token=access_token)


def ga4_data_client(access_token: str):
    """Analytics Data API client (run_report / run_realtime_report)."""
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    return BetaAnalyticsDataClient(credentials=_credentials(access_token))


def ga4_admin_client(access_token: str):
    """Analytics Admin API client (list account summaries / properties)."""
    from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
    return AnalyticsAdminServiceClient(credentials=_credentials(access_token))
