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
from aepp import configs,ConnectObject
from unittest.mock import patch, MagicMock, Mock, ANY

@patch("aepp.configs.importConfigFile")
def test_importConfigFile_Oauth(mock_data):
    mock_data.return_value = {
        "org_id": "<orgID>",
        "client_id": "<client_id>",
        "secret": "<YourSecret>",
        "sandbox-name": "prod",
        "environment": "prod",
        "scopes":"scopes"
    }
    assert(type(mock_data.return_value),dict)


class ConnectInstanceTest(unittest.TestCase):

    @patch("aepp.connector.AdobeRequest")
    def test_instanceCreation(self,mock_connector):
        mock_data = {
        "org_id": "orgID",
        "client_id": "client_id",
        "secret": "YourSecret",
        "sandbox-name": "prod",
        "environment": "prod",
        "scopes":"scopes"
        }
        instance_conn = mock_connector.return_value
        instance_conn.postData.return_value = {'foo'}
        self.mock_ConnectObject = ConnectObject(config=mock_data)
        self.mock_ConnectObject.connect()
        self.assertIsNotNone(self.mock_ConnectObject.connectionType)
    
    @patch("aepp.connector.AdobeRequest")
    def test_setOauthV2Setup(self,mock_connector):
        mock_data = {
        "org_id": "orgID",
        "client_id": "client_id",
        "secret": "YourSecret",
        "sandbox-name": "prod",
        "environment": "prod",
        "scopes":"scopes"
        }
        self.mock_ConnectObject = ConnectObject(config=mock_data)
        self.mock_ConnectObject.connect()
        self.mock_ConnectObject.connectionType = 'oauthV2'
        self.mock_ConnectObject.setOauthV2setup(MagicMock(),MagicMock())
        assert(self.mock_ConnectObject.credentialId is not None)
        assert(self.mock_ConnectObject.orgDevId is not None)


    @patch("aepp.connector.AdobeRequest")
    def test_setOauthV2Setup(self,mock_connector):
        mock_data = {
        "org_id": "orgID",
        "client_id": "client_id",
        "secret": "YourSecret",
        "sandbox-name": "prod",
        "environment": "prod",
        "scopes":"scopes"
        }
        self.mock_ConnectObject = ConnectObject(config=mock_data)
        self.mock_ConnectObject.connect()
        with self.assertRaises(Exception) as cm:
            self.mock_ConnectObject.setOauthV2setup(MagicMock(),MagicMock())
            self.assertEqual('You are trying to set credential ID or orgDevId for auth that is not OauthV2. We do not support these auth type.', str(cm.exception))