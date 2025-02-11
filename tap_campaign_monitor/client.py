import requests
import requests.auth
import singer
import singer.metrics
import time
import pytz

import tap_campaign_monitor.timezones

LOGGER = singer.get_logger()  # noqa


class CampaignMonitorClient:

    def __init__(self, config):
        self.config = config
        self.timezone = self.get_timezone()
        LOGGER.info("Client timezone is {}".format(self.timezone))

    def get_authorization(self):
        return requests.auth.HTTPBasicAuth(self.config.get("api_key"), "x")


    def get_timezone(self):
        url = (
            'https://api.createsend.com/api/v3.2/clients/{}.json'
            .format(self.config.get('client_id'))
        )

        result = self.make_request(url, 'GET')

        timezone = result.get('BasicDetails', {}).get('TimeZone')

        return tap_campaign_monitor.timezones.from_string(timezone)

    def make_request(self, url, method, base_backoff=30,
                     params=None, body=None):

        LOGGER.info("Making {} request to {}".format(method, url))
        auth = self.get_authorization()

        response = requests.request(
            method,
            url,
            headers={'Content-Type': 'application/json'},
            auth=auth,
            params=params,
            json=body)

        if response.status_code in [429, 504]:
            if base_backoff > 120:
                raise RuntimeError('Backed off too many times, exiting!')

            LOGGER.warn('Sleeping for {} seconds and trying again'
                        .format(base_backoff))

            time.sleep(base_backoff)

            return self.make_request(
                url, method, base_backoff * 2, params, body)

        elif response.status_code != 200:
            raise RuntimeError(response.text)

        return response.json()
