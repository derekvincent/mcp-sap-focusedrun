import asyncio
import hashlib
import logging
import time
from typing import List, Optional, Any
from contextvars import ContextVar

import httpx
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Context variable to store request-specific overrides from headers
request_config_overrides: ContextVar[dict] = ContextVar("request_config_overrides", default={})


class FocusedRun:
    """
    Client for SAP Focused Run LMDB Public API.
    https://support.sap.com/en/alm/sap-focused-run/expert-portal/frun-lmdb-main/frun-lmdb-public-api.html
    """

    LANDSCAPE_API_HOSTS = "landscape_api_hosts"
    LANDSCAPE_API_SYSTEMS = "landscape_api_systems"
    LANDSCAPE_API_TECHNICAL_INSTANCES = "landscape_api_technical_instances"
    LANDSCAPE_API_SOFTWARE_COMPONENTS = "landscape_api_installed_software_components"
    LANDSCAPE_API_PRODUCT_VERSIONS = "landscape_api_installed_product_versions"
    LANDSCAPE_API_ABAP_CLIENTS = "landscape_api_abap_clients"
    LANDSCAPE_API_SINGLE_DATABASE = "landscape_api_single_database"

    def __init__(
        self, 
        base_url: str, 
        sap_client: str, 
        api_key: str, 
        api_user: str, 
        api_password: str, 
        cache_ttl=300, 
        cache_maxsize=100, 
        additional_headers: dict = None
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_user = api_user
        self.api_password = api_password
        self.sap_client = sap_client
        self.cache = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)
        self.additional_headers = additional_headers or {}
        
        # Production-ready AsyncClient with connection pooling and sensible timeouts.
        # follow_redirects=False is crucial for APIs to detect Auth blocks (302 redirects)
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            follow_redirects=False
        )

    async def close(self):
        """Close the underlying HTTP client."""
        await self.client.aclose()

    # Private Methods
    def __redact(self, value: str) -> str:
        """Helper to redact sensitive strings for logging."""
        if not value or len(value) < 8:
            return "***"
        return f"{value[:3]}...{value[-3:]}"

    def __get_identity_hash(self, base_url, api_user, sap_client, headers) -> str:
        """
        Creates a unique hash for the current connection identity.
        This ensures strict cache isolation between different tenants/credentials.
        """
        identity_str = f"{base_url}|{api_user}|{sap_client}|{headers.get('APIKey', '')}|{headers.get('CF-Access-Client-Id', '')}"
        return hashlib.sha256(identity_str.encode()).hexdigest()

    def __build_filter(self, field: str, values: List[str]) -> str:
        conditions = [f"{field} eq '{val}'" for val in values]
        return f"({' or '.join(conditions)})"

    # Generic Request Handler
    async def _make_request(self, endpoint: str, **kwargs) -> dict:
        """Helper method to make GET requests to the LMDB API with retries and caching."""
        overrides = request_config_overrides.get()
        
        base_url = overrides.get("base_url", self.base_url)
        api_user = overrides.get("api_user", self.api_user)
        api_password = overrides.get("api_password", self.api_password)
        sap_client = overrides.get("sap_client", self.sap_client)
        
        url = f"{base_url}/{endpoint}?sap-client={sap_client}"
        auth = httpx.BasicAuth(username=api_user, password=api_password)
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        headers.update(self.additional_headers)
        
        if "cf_id" in overrides:
            headers["CF-Access-Client-Id"] = overrides["cf_id"]
        if "cf_secret" in overrides:
            headers["CF-Access-Client-Secret"] = overrides["cf_secret"]
        if self.api_key:
            headers["APIKey"] = self.api_key

        # Cache check with strict identity isolation
        identity_hash = self.__get_identity_hash(base_url, api_user, sap_client, headers)
        cache_key = (endpoint, frozenset(kwargs.items()), identity_hash)
        
        if cache_key in self.cache:
            logger.info(f"Cache hit for endpoint: {endpoint} | Identity: {identity_hash[:8]}")
            return self.cache[cache_key]

        # Retry logic for transient errors (502, 503, 504)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"SAP LMDB Request | endpoint: {endpoint} | base_url: {base_url} | user: {self.__redact(api_user)}")
                
                response = await self.client.get(
                    url, headers=headers, auth=auth, params=kwargs
                )
                
                # Check for redirects (often identity provider blocks)
                if response.status_code in [301, 302, 303, 307, 308]:
                    location = response.headers.get("Location", "Unknown")
                    logger.error(f"Authentication Blocked (Redirected to: {location})")
                    return {
                        "error": "Authentication Blocked",
                        "details": f"The request was redirected to {location}. Please check your Cloudflare Access or SAP credentials."
                    }

                # If we get a transient error, retry
                if response.status_code in [502, 503, 504] and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Transient error {response.status_code}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                
                # Verify we actually got JSON before parsing
                content_type = response.headers.get("Content-Type", "")
                if "application/json" not in content_type:
                    logger.error(f"Unexpected response format: {content_type}")
                    return {
                        "error": "Unexpected response format",
                        "details": f"Expected JSON but received {content_type}. Body starts with: {response.text[:100]}..."
                    }

                data = response.json()

                # Client-side pagination fallback
                if isinstance(data, list):
                    if "$skip" in kwargs:
                        data = data[int(kwargs["$skip"]) :]
                    if "$top" in kwargs:
                        data = data[: int(kwargs["$top"])]

                self.cache[cache_key] = data
                return data

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} for {endpoint}: {e.response.text}")
                return {
                    "error": f"HTTP status error: {e.response.status_code}",
                    "details": e.response.text,
                }
            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Network error: {str(e)}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"Network error for {endpoint}: {e}")
                return {
                    "error": "Network error occurred",
                    "details": str(e),
                }
            except Exception as e:
                logger.exception(f"Unexpected error during request: {e}")
                return {"error": "An unexpected error occurred", "details": str(e)}
        
        return {"error": "Max retries exceeded"}

    # Public Methods
    async def get_hosts(self, hostnames: List[str] = None, customer_names: List[str] = None, customer_networks: List[str] = None, **kwargs) -> dict:
        filters = []
        if hostnames: filters.append(self.__build_filter("HOST_NAME", hostnames))
        if customer_names: filters.append(self.__build_filter("CUSTOMER_NAME", customer_names))
        if customer_networks: filters.append(self.__build_filter("CUSTOMER_NETWORK", customer_networks))
        if filters: kwargs["$filter"] = " and ".join(filters)
        return await self._make_request(self.LANDSCAPE_API_HOSTS, **kwargs)

    async def get_systems(self, system_ids: List[str] = None, customer_names: List[str] = None, system_types: List[str] = None, **kwargs) -> dict:
        filters = []
        if system_ids: filters.append(self.__build_filter("EXTENDED_SID", system_ids))
        if customer_names: filters.append(self.__build_filter("CUSTOMER_NAME", customer_names))
        if system_types: filters.append(self.__build_filter("SYSTEM_TYPE", system_types))
        if filters: kwargs["$filter"] = " and ".join(filters)
        return await self._make_request(self.LANDSCAPE_API_SYSTEMS, **kwargs)

    async def get_technical_instances(self, system_ids: List[str] = None, **kwargs) -> dict:
        filters = []
        if system_ids: filters.append(self.__build_filter("EXTENDED_SID", system_ids))
        if filters: kwargs["$filter"] = " and ".join(filters)
        return await self._make_request(self.LANDSCAPE_API_TECHNICAL_INSTANCES, **kwargs)

    async def get_databases(self, system_ids: List[str] = None, customer_names: List[str] = None, **kwargs) -> dict:
        return await self.get_systems(system_ids=system_ids, customer_names=customer_names, system_types=["DATABASE"], **kwargs)

    async def get_cloud_tenants(self, tenant_ids: List[str] = None, customer_names: List[str] = None, **kwargs) -> dict:
        return await self.get_systems(system_ids=tenant_ids, customer_names=customer_names, system_types=["CLOUD_SERVICE"], **kwargs)

    async def get_installed_software_components(self, system_ids: List[str] = None, **kwargs) -> dict:
        filters = []
        if system_ids: filters.append(self.__build_filter("EXTENDED_SID", system_ids))
        if filters: kwargs["$filter"] = " and ".join(filters)
        return await self._make_request(self.LANDSCAPE_API_SOFTWARE_COMPONENTS, **kwargs)

    async def get_installed_product_versions(self, system_ids: List[str] = None, **kwargs) -> dict:
        filters = []
        if system_ids: filters.append(self.__build_filter("EXTENDED_SID", system_ids))
        if filters: kwargs["$filter"] = " and ".join(filters)
        return await self._make_request(self.LANDSCAPE_API_PRODUCT_VERSIONS, **kwargs)

    async def get_abap_clients(self, system_ids: List[str] = None, **kwargs) -> dict:
        filters = []
        if system_ids: filters.append(self.__build_filter("EXTENDED_SID", system_ids))
        if filters: kwargs["$filter"] = " and ".join(filters)
        return await self._make_request(self.LANDSCAPE_API_ABAP_CLIENTS, **kwargs)

    async def get_single_database(self, **kwargs) -> dict:
        return await self._make_request(self.LANDSCAPE_API_SINGLE_DATABASE, **kwargs)

    async def get_customers(self, customer_network_id: str = None, search_query: str = None, top: int = 50, skip: int = 0, **kwargs) -> dict:
        """
        Retrieves a deduplicated list of customers from the product versions endpoint.
        Performs client-side filtering to avoid SAP LMDB OData 400 errors with complex OR filters.
        Fetches multiple pages from SAP to ensure exhaustive coverage in large landscapes.
        """
        endpoint = self.LANDSCAPE_API_PRODUCT_VERSIONS
        
        # Limit fields to minimize data transfer
        kwargs["$select"] = "CUSTOMER_NETWORK,CUSTOMER_NETWORK_NAME,CUSTOMER_NAME"
        
        # 1. Base Filter (ID only if provided)
        if customer_network_id:
            kwargs["$filter"] = f"CUSTOMER_NETWORK eq '{customer_network_id}'"
        
        # 2. Exhaustive Fetch with Pagination
        # We fetch in batches until we reach the end of the landscape data.
        all_results = []
        batch_size = 2000
        current_skip = 0
        max_total_fetch = 20000 # Safety limit to prevent runaway memory usage
        
        while True:
            fetch_kwargs = kwargs.copy()
            fetch_kwargs["$top"] = batch_size
            fetch_kwargs["$skip"] = current_skip
            
            data = await self._make_request(endpoint, **fetch_kwargs)
            if "error" in data:
                # If we already have some results, we'll process those instead of failing
                if all_results: break 
                return data

            results = data if isinstance(data, list) else data.get("d", {}).get("results", [])
            if not isinstance(results, list) or not results:
                break
                
            all_results.extend(results)
            
            # If the server returned fewer records than we asked for, we reached the end
            if len(results) < batch_size:
                break
                
            current_skip += len(results)
            if current_skip >= max_total_fetch:
                logger.warning(f"Customer search reached safety limit of {max_total_fetch} records. Results may be incomplete.")
                break

        # 3. Deduplicate and Filter Client-Side
        unique_customers = {}
        q = search_query.strip().lower() if search_query else None
        
        for r in all_results:
            cid = r.get("CUSTOMER_NETWORK")
            if not cid:
                continue
                
            c_name = (r.get("CUSTOMER_NAME") or "")
            cn_name = (r.get("CUSTOMER_NETWORK_NAME") or "")
            
            # Apply fuzzy filter if query provided
            if q:
                if q not in c_name.lower() and \
                   q not in cn_name.lower() and \
                   q not in cid.lower():
                    continue

            if cid not in unique_customers:
                unique_customers[cid] = {
                    "CUSTOMER_NETWORK": cid,
                    "CUSTOMER_NETWORK_NAME": cn_name,
                    "CUSTOMER_NAME": c_name
                }
        
        customer_list = list(unique_customers.values())
        total_found = len(customer_list)
        
        # Apply pagination to the deduplicated list for the LLM's response
        paginated_list = customer_list[skip : skip + top]

        return {
            "customers": paginated_list,
            "total_count": total_found,
            "top": top,
            "skip": skip,
            "fetched_records": len(all_results)
        }
