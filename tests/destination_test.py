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
from aepp.destination import Authoring
from unittest.mock import patch, MagicMock, ANY

class DestinationTest(unittest.TestCase):
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
    destination_list_response = [
        {"id": "destination1"},
        {"id": "destination2"}
    ]
    destination_response = {"id": "test_destination_id"}
    destination_server_list_response = [
        {"id": "server1"},
        {"id": "server2"}
    ]
    destination_server_response = {
        "id": "test_server"
    }
    audience_template_list = [
        {"id": "test1"},
        {"id": "test2"}
    ]
    audience_template_response = {
        "id": "test_audience_template_id"
    }
    credential_list_response = [
        {"id": "test_credential_1"}, {"id": "test_credential_2"}
    ]
    credential_response = {
        "id": "test_credential_id"
    }

    sample_profile = {
        "name": "test_sample_profile"
    }
    sample_destination = {
        "name": "sample_destination"
    }

    @patch("aepp.connector.AdobeRequest.getData", return_value = destination_list_response)
    def test_get_destinations(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.getDestinations()
        mock_connector.assert_called_once_with(ANY)
        assert res == self.destination_list_response

    @patch("aepp.connector.AdobeRequest.getData", return_value = destination_response)
    def test_get_destination(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.getDestination(destinationId="test_destination_id")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.destination_response

    @patch("aepp.connector.AdobeRequest.deleteData", return_value = destination_response)
    def test_delete_destination(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.deleteDestination(destinationId="test_delete_destination_id")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.destination_response

    def test_create_destination_with_invalid_input(self):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        try:
            destination_instance.createDestination(destinationObj="test")
            self.fail("Expect an exception")
        except Exception as e:
            assert str(e) == "Require a dictionary defining the destination configuration"

    @patch("aepp.connector.AdobeRequest.postData", return_value = destination_response)
    def test_create_destination(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.createDestination(destinationObj=self.destination_response)
        mock_connector.assert_called_once_with(ANY, data = {'id': 'test_destination_id'})
        assert res == self.destination_response

    @patch("aepp.connector.AdobeRequest.putData", return_value = destination_response)
    def test_update_destination(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.updateDestination(destinationId="test_update", destinationObj={"destination": "update"})
        mock_connector.assert_called_once_with(ANY, data = {"destination": "update"})
        assert res == self.destination_response

    @patch("aepp.connector.AdobeRequest.getData", return_value = destination_server_list_response)
    def test_get_destination_server_list(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.getDestinationServers()
        mock_connector.assert_called_once_with(ANY)
        assert res == self.destination_server_list_response

    @patch("aepp.connector.AdobeRequest.getData", return_value = destination_server_response)
    def test_get_destination_server_by_id(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.getDestinationServer(serverId="test_server_id")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.destination_server_response

    @patch("aepp.connector.AdobeRequest.deleteData", return_value = destination_server_response)
    def test_delete_destination_server_by_id(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.deleteDestinationServer(serverId="test_server_id")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.destination_server_response

    @patch("aepp.connector.AdobeRequest.putData", return_value = destination_server_response)
    def test_update_destination_server(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.updateDestinationServer(serverId="test_server_id", serverObj=self.destination_server_response)
        mock_connector.assert_called_once_with(ANY, data={'id': 'test_server'} )
        assert res == self.destination_server_response

    @patch("aepp.connector.AdobeRequest.getData", return_value = audience_template_list)
    def test_get_audience_template_list(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.getAudienceTemplates()
        mock_connector.assert_called_once_with(ANY)
        assert res == self.audience_template_list

    @patch("aepp.connector.AdobeRequest.getData", return_value = audience_template_response)
    def test_get_audience_template_by_id(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.getAudienceTemplate(audienceId="test_audience_template_id")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.audience_template_response

    @patch("aepp.connector.AdobeRequest.deleteData", return_value = audience_template_response)
    def test_delete_audience_template(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.deleteAudienceTemplate(audienceId="test_audience_template_id")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.audience_template_response

    @patch("aepp.connector.AdobeRequest.postData", return_value = audience_template_response)
    def test_create_audience_template(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.createAudienceTemplate(templateObj=self.audience_template_response)
        mock_connector.assert_called_once_with(ANY, data = self.audience_template_response)
        assert res == self.audience_template_response

    @patch("aepp.connector.AdobeRequest.postData", return_value = audience_template_response)
    def test_update_audience_template(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.updateAudienceTemplate(audienceId="test_audience_template_id", templateObj=self.audience_template_response)
        mock_connector.assert_called_once_with(ANY, data = self.audience_template_response)
        assert res == self.audience_template_response

    @patch("aepp.connector.AdobeRequest.getData", return_value = credential_list_response)
    def test_get_credential_list(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.getCredentials()
        mock_connector.assert_called_once_with(ANY)
        assert res == self.credential_list_response

    @patch("aepp.connector.AdobeRequest.getData", return_value = credential_response)
    def test_get_credential_by_id(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.getCredential(credentialId="test_credential_id")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.credential_response

    @patch("aepp.connector.AdobeRequest.deleteData", return_value = credential_response)
    def test_delete_credential_by_id(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.deleteCredential(credentialId="test_credential_id")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.credential_response

    @patch("aepp.connector.AdobeRequest.postData", return_value = credential_response)
    def test_create_credential(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.createCredential(credentialObj=self.credential_response)
        mock_connector.assert_called_once_with(ANY, data={'id': 'test_credential_id'})
        assert res == self.credential_response

    @patch("aepp.connector.AdobeRequest.putData", return_value = credential_response)
    def test_update_credential(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.updateCredential(credentialId= "test_credential_id", credentialObj=self.credential_response)
        mock_connector.assert_called_once_with(ANY, data={'id': 'test_credential_id'})
        assert res == self.credential_response

    @patch("aepp.connector.AdobeRequest.getData", return_value = sample_profile)
    def test_get_sample_profile(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.getSampleProfile(destinationInstanceId= "test_instance_id", destinationId="test_destination_id")
        mock_connector.assert_called_once_with(ANY, params={
            "destinationInstanceId" : "test_instance_id",
            "destinationId" : "test_destination_id",
            "count" : 100
        })
        assert res == self.sample_profile

    @patch("aepp.connector.AdobeRequest.getData", return_value = sample_destination)
    def test_get_sample_destination(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.getSampleDestination(destinationConfigId="test_destination_id")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.sample_destination

    @patch("aepp.connector.AdobeRequest.postData", return_value = sample_destination)
    def test_generate_profile(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.generateTestProfile(destinationId="test_destination_id", template="test")
        mock_connector.assert_called_once_with(ANY, data = {
            "destinationId": "test_destination_id",
            "template": "test",
        })
        assert res == self.sample_destination

    @patch("aepp.connector.AdobeRequest.postData", return_value = sample_destination)
    def test_send_message(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.sendMessageToPartner(destinationInstanceId="test", profiles=["1", "2"])
        mock_connector.assert_called_once_with(ANY, data = ["1", "2"])
        assert res == self.sample_destination

    @patch("aepp.connector.AdobeRequest.getData", return_value = destination_list_response)
    def test_get_submission_list(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.getSubmissions()
        mock_connector.assert_called_once_with(ANY)
        assert res == self.destination_list_response

    @patch("aepp.connector.AdobeRequest.getData", return_value = destination_response)
    def test_get_submission_by_id(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.getSubmission(destinationConfigId="test")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.destination_response

    @patch("aepp.connector.AdobeRequest.postData", return_value = destination_response)
    def test_submit_destination(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.SubmitDestination(destinationObj=self.destination_response)
        mock_connector.assert_called_once_with(ANY, data = self.destination_response)
        assert res == self.destination_response

    @patch("aepp.connector.AdobeRequest.putData", return_value = destination_response)
    def test_update_submission(self, mock_connector):
        destination_instance = Authoring(config=self.config, header=MagicMock())
        res = destination_instance.updateSubmissionRequest(destinationConfigId= "test", destinationObj=self.destination_response)
        mock_connector.assert_called_once_with(ANY, data = self.destination_response)
        assert res == self.destination_response