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
from aepp.sandboxes import Sandboxes
from unittest.mock import patch, MagicMock, ANY


class SandboxTest(unittest.TestCase):
    config = {
        "org_id": "3ADF23C463D98F640A494032@AdobeOrg",
        "client_id": "35e6e4d205274c4ca1418805ac41153b",
        "tech_id": "test005@techacct.adobe.com",
        "pathToKey": "/Users/Downloads/config/private.key",
        "auth_code": "",
        "secret": "test",
        "date_limit": 0,
        "sandbox": "prod",
        "environment": "stage",
        "token": "token",
        "jwtTokenEndpoint": "https://ims-na1.adobelogin.com/ims/exchange/jwt/",
        "oauthTokenEndpoint": "",
        "imsEndpoint": "https://ims-na1-stg1.adobelogin.com",
        "private_key": ""
    }
    sandbox_instance = Sandboxes(config=config, header=MagicMock())
    sandbox_list_response = {
        "sandboxes": ["test1", "test2"]
    }

    sandbox_type_list_response = {
        "sandboxTypes": ["type1", "type2"]
    }

    sandbox_payload = {"name": "test", "title": "test", "type": "development"}
    sandbox_payload_with_id = {"id":"test_sandbox_id", "name": "test", "title": "test", "type": "development"}

    @patch("aepp.connector.AdobeRequest.getData", return_value = sandbox_list_response)
    def test_get_sandboxes(self, mock_connector):
        res = self.sandbox_instance.getSandboxes()
        assert (res == ["test1", "test2"])

    @patch("aepp.connector.AdobeRequest.getData", return_value = sandbox_type_list_response)
    def test_get_sandbox_types(self, mock_connector):
        res = self.sandbox_instance.getSandboxTypes()
        assert (res == ["type1", "type2"])

    def test_create_sandbox_without_name(self):
        try:
            self.sandbox_instance.createSandbox(name = None)
            self.fail("expect an excepton")
        except Exception as e:
            assert(str(e) == "name and title cannot be empty")

    @patch("aepp.connector.AdobeRequest.postData", return_value = sandbox_payload)
    def test_create_sandbox(self, mock_connector):
        res = self.sandbox_instance.createSandbox(name="test", title="test")
        mock_connector.assert_called_once_with(ANY, data=self.sandbox_payload)
        assert (res == self.sandbox_payload)

    @patch("aepp.connector.AdobeRequest.getData", return_value = sandbox_payload)
    def test_get_sandbox(self, mock_connector):
        res = self.sandbox_instance.getSandbox(name = "test")
        mock_connector.assert_called_once_with("/data/foundation/sandbox-management/sandboxes/test")
        assert (res == self.sandbox_payload)

    @patch("aepp.connector.AdobeRequest.getData", return_value = sandbox_payload_with_id)
    def test_get_sandbox_id(self, mock_connector):
        res = self.sandbox_instance.getSandboxId(name = "test")
        mock_connector.assert_called_once_with("/data/foundation/sandbox-management/sandboxes/test")
        assert (res == "test_sandbox_id")
    @patch("aepp.connector.AdobeRequest.deleteData", return_value = sandbox_payload)
    def test_delete_sandbox(self, mock_connector):
        res = self.sandbox_instance.deleteSandbox(name = "test-delete")
        mock_connector.assert_called_once_with("/data/foundation/sandbox-management/sandboxes/test-delete")
        assert (res == self.sandbox_payload)

    @patch("aepp.connector.AdobeRequest.putData", return_value = sandbox_payload)
    def test_reset_sandbox(self, mock_connector):
        res = self.sandbox_instance.resetSandbox(name = "test-reset")
        mock_connector.assert_called_once_with("/data/foundation/sandbox-management/sandboxes/test-reset", data = {'action':'reset'})
        assert (res == self.sandbox_payload)

    @patch("aepp.connector.AdobeRequest.patchData", return_value = sandbox_payload)
    def test_update_sandbox(self, mock_connector):
        res = self.sandbox_instance.updateSandbox(name = "test-update", action={"update": "test"})
        mock_connector.assert_called_once_with("/data/foundation/sandbox-management/sandboxes/test-update", data= {"update": "test"})
        assert (res == self.sandbox_payload)
