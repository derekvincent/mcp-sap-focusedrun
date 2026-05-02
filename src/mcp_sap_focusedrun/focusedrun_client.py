import logging
from typing import List

import httpx
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class FocusedRun:
    """
    https://support.sap.com/en/alm/sap-focused-run/expert-portal/frun-lmdb-main/frun-lmdb-public-api.html
    """

    LANDSCAPE_API_HOSTS = "landscape_api_hosts"
    LANDSCAPE_API_SYSTEMS = "landscape_api_systems"
    LANDSCAPE_API_TECHNICAL_INSTANCES = "landscape_api_technical_instances"
    LANDSCAPE_API_SOFTWARE_COMPONENTS = "landscape_api_installed_software_components"
    LANDSCAPE_API_PRODUCT_VERSIONS = "landscape_api_installed_product_versions"
    LANDSCAPE_API_ABAP_CLIENTS = "landscape_api_abap_clients"
    LANDSCAPE_API_SINGLE_DATABASE = "landscape_api_single_database"
    LANDSCAPE_API_HOSTS_FILTERS = {
        "HOST_NAME",
        "NAMETYPE",
        "DATA_CENTER",
        "CUSTOMER_NAME",
        "CUSTOMER_NETWORK",
    }

    def __init__(self, base_url, sap_client, api_key, api_user, api_password, cache_ttl=300, cache_maxsize=100):
        self.base_url = base_url.rstrip("/")  # Ensure no trailing slash
        self.api_key = api_key
        self.api_user = api_user
        self.api_password = api_password
        self.sap_client = sap_client
        self.cache = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)

    # Private Methods
    # Filter builders
    def __build_filter(self, field: str, values: List[str]) -> str:
        conditions = [f"{field} eq '{val}'" for val in values]
        return f"({' or '.join(conditions)})"

    def __filter_hostnames(self, hostnames: List[str]) -> str:
        return self.__build_filter("HOST_NAME", hostnames)

    def __filter_customer_names(self, customer_names: List[str]) -> str:
        return self.__build_filter("CUSTOMER_NAME", customer_names)

    def __filter_customer_networks(self, customer_networks: List[str]) -> str:
        return self.__build_filter("CUSTOMER_NETWORK", customer_networks)

    # Generic Request Handler
    def _make_request(self, endpoint: str, **kwargs) -> dict:
        """Helper method to make GET requests to the LMDB API."""
        # Create a unique, hashable key for this specific request
        cache_key = (endpoint, frozenset(kwargs.items()))
        if cache_key in self.cache:
            logger.info(
                f"Cache hit for SAP LMDB endpoint: {endpoint} | params: {kwargs}"
            )
            return self.cache[cache_key]

        url = f"{self.base_url}/{endpoint}?sap-client={self.sap_client}"
        auth = httpx.BasicAuth(username=self.api_user, password=self.api_password)
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["APIKey"] = self.api_key

        try:
            logger.info(f"Requesting SAP LMDB endpoint: {endpoint} | params: {kwargs}")
            response = httpx.get(
                url, headers=headers, auth=auth, params=kwargs, timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            # Fallback: Enforce pagination client-side if SAP ignored $top or $skip
            if isinstance(data, list):
                if "$skip" in kwargs:
                    data = data[int(kwargs["$skip"]) :]
                if "$top" in kwargs:
                    data = data[: int(kwargs["$top"])]

            self.cache[cache_key] = data
            return data
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error {e.response.status_code} for {e.request.url!r}: {e.response.text}"
            )
            return {
                "error": f"HTTP status error: {e.response.status_code}",
                "details": e.response.text,
            }
        except httpx.RequestError as e:
            logger.error(f"Network error for {e.request.url!r}: {e}")
            return {
                "error": f"Network error occurred while requesting {e.request.url!r}",
                "details": str(e),
            }
        except Exception as e:
            logger.exception(f"Unexpected error during SAP LMDB request: {e}")
            return {"error": "An unexpected error occurred", "details": str(e)}

    # Public Methods
    # Host APIs
    def get_hosts(
        self,
        hostnames: List[str] = None,
        customer_names: List[str] = None,
        customer_networks: List[str] = None,
        **kwargs,
    ) -> dict:
        filters = []
        if hostnames:
            filters.append(self.__filter_hostnames(hostnames))
        if customer_names:
            filters.append(self.__filter_customer_names(customer_names))
        if customer_networks:
            filters.append(self.__filter_customer_networks(customer_networks))

        if filters:
            kwargs["$filter"] = " and ".join(filters)
        return self._make_request(self.LANDSCAPE_API_HOSTS, **kwargs)

    # System APIs
    def get_systems(
        self,
        system_ids: List[str] = None,
        customer_names: List[str] = None,
        system_types: List[str] = None,
        **kwargs,
    ) -> dict:
        filters = []
        if system_ids:
            filters.append(self.__build_filter("EXTENDED_SID", system_ids))
        if customer_names:
            filters.append(self.__build_filter("CUSTOMER_NAME", customer_names))
        if system_types:
            filters.append(self.__build_filter("SYSTEM_TYPE", system_types))

        if filters:
            kwargs["$filter"] = " and ".join(filters)
        return self._make_request(self.LANDSCAPE_API_SYSTEMS, **kwargs)

    # Technical Instance APIs
    def get_technical_instances(
        self, system_ids: List[str] = None, **kwargs
    ) -> dict:
        filters = []
        if system_ids:
            filters.append(self.__build_filter("EXTENDED_SID", system_ids))

        if filters:
            kwargs["$filter"] = " and ".join(filters)
        return self._make_request(self.LANDSCAPE_API_TECHNICAL_INSTANCES, **kwargs)

    # Database APIs
    def get_databases(
        self, system_ids: List[str] = None, customer_names: List[str] = None, **kwargs
    ) -> dict:
        # Under the hood, we route databases securely through the systems endpoint
        return self.get_systems(
            system_ids=system_ids,
            customer_names=customer_names,
            system_types=["DATABASE"],
            **kwargs,
        )

    # Cloud Tenant APIs
    def get_cloud_tenants(
        self, tenant_ids: List[str] = None, customer_names: List[str] = None, **kwargs
    ) -> dict:
        # Under the hood, we route cloud tenants securely through the systems endpoint
        # Mapping tenant_ids to system_ids (EXTENDED_SID) to match the SAP systems schema
        return self.get_systems(
            system_ids=tenant_ids,
            customer_names=customer_names,
            system_types=["CLOUD_SERVICE"],
            **kwargs,
        )

    # Installed Software Components APIs
    def get_installed_software_components(
        self, system_ids: List[str] = None, **kwargs
    ) -> dict:
        filters = []
        if system_ids:
            filters.append(self.__build_filter("EXTENDED_SID", system_ids))
        if filters:
            kwargs["$filter"] = " and ".join(filters)
        return self._make_request(self.LANDSCAPE_API_SOFTWARE_COMPONENTS, **kwargs)

    # Installed Product Versions APIs
    def get_installed_product_versions(
        self, system_ids: List[str] = None, **kwargs
    ) -> dict:
        filters = []
        if system_ids:
            filters.append(self.__build_filter("EXTENDED_SID", system_ids))
        if filters:
            kwargs["$filter"] = " and ".join(filters)
        return self._make_request(self.LANDSCAPE_API_PRODUCT_VERSIONS, **kwargs)

    # ABAP Clients APIs
    def get_abap_clients(self, system_ids: List[str] = None, **kwargs) -> dict:
        filters = []
        if system_ids:
            filters.append(self.__build_filter("EXTENDED_SID", system_ids))
        if filters:
            kwargs["$filter"] = " and ".join(filters)
        return self._make_request(self.LANDSCAPE_API_ABAP_CLIENTS, **kwargs)

    # Explicit Single Database API
    def get_single_database(self, **kwargs) -> dict:
        return self._make_request(self.LANDSCAPE_API_SINGLE_DATABASE, **kwargs)
