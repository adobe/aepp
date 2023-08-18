#  Copyright 2023 Adobe. All rights reserved.
#  This file is licensed to you under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License. You may obtain a copy
#  of the License at http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software distributed under
#  the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#  OF ANY KIND, either express or implied. See the License for the specific language
#  governing permissions and limitations under the License.

import unittest
from aepp.accesscontrol import AccessControl
from unittest.mock import patch, MagicMock, ANY
import time

class AccessControlTest(unittest.TestCase):
    config = {
        "org_id": "3ADF23C463D98F640A494032@AdobeOrg",
        "client_id": "35e6e4d205274c4ca1418805ac41153b",
        "tech_id": "test005@techacct.adobe.com",
        "pathToKey": "/Users/Downloads/config/private.key",
        "auth_code": "",
        "secret": "test",
        "date_limit": time.time() + 60 * 30,
        "sandbox": "prod",
        "environment": "stage",
        "token": "token",
        "jwtTokenEndpoint": "https://ims-na1.adobelogin.com/ims/exchange/jwt/",
        "oauthTokenEndpoint": "",
        "imsEndpoint": "https://ims-na1-stg1.adobelogin.com",
        "private_key": ""
    }

    @patch("aepp.connector.AdobeRequest.getData", return_value = MagicMock())
    def test_get_reference(self, mock_connector):
        access_control_instance = AccessControl(config=self.config, header=MagicMock())
        access_control_instance.getReferences()

    def test_post_effective_policies_with_invalid_input(self):
        access_control_instance = AccessControl(config=self.config, header=MagicMock())
        try:
            access_control_instance.postEffectivePolicies(listElements="test")
            self.fail("expect a type error")
        except TypeError:
            pass

    @patch("aepp.connector.AdobeRequest.postData", return_value = {"result"})
    def test_post_effective_policies(self, mock_connector):
        access_control_instance = AccessControl(config=self.config, header=MagicMock())
        result = access_control_instance.postEffectivePolicies(["test"])
        assert (result == {"result"})
