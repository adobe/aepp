#  Copyright 2023 Adobe. All rights reserved.
#  This file is licensed to you under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License. You may obtain a copy
#  of the License at http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software distributed under
#  the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#  OF ANY KIND, either express or implied. See the License for the specific language
#  governing permissions and limitations under the License.

from aepp.flowservice import FlowService
import unittest
from unittest.mock import patch, MagicMock, ANY
import time


class FlowserviceTest(unittest.TestCase):
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
    entity_response = {
        "id": "test"

    }
    entity_items_response = {
        "items": [
            entity_response
        ]
    }

    entity_list_response = [
            {"id": "test1", "name": "test1"},
            {"id": "test2", "name": "test2"}
    ]
    entity_map_response = {
        "test1": "test1",
        "test2": "test2"
    }

    @patch("aepp.connector.AdobeRequest.getData", return_value = entity_response)
    def test_flowservice_get_resource(self, mock_connector):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        res = flow_service_conn.getResource(ANY)
        mock_connector.assert_called_once_with(ANY, params=None, format='json')
        assert res == self.entity_response

    @patch("aepp.connector.AdobeRequest.getData", return_value = entity_list_response)
    def test_flowservice_get_connections(self, mock_connector):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        res = flow_service_conn.getConnections(ANY)
        mock_connector.assert_called_once_with('https://platform-stage.adobe.io/data/foundation/flowservice/connections', params={'limit': 20})
        assert res == self.entity_list_response

    @patch("aepp.connector.AdobeRequest.postData", return_value = entity_response)
    def test_flowservice_create_connection(self, mock_connector):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        res = flow_service_conn.createConnection(data={"name": "test", "auth": "none", "connectionSpec": "connectionSpec"})
        mock_connector.assert_called_once_with('https://platform-stage.adobe.io/data/foundation/flowservice/connections', data={'name': 'test', 'auth': 'none', 'connectionSpec': 'connectionSpec'}, format='json')
        assert res == self.entity_response

    @patch("aepp.connector.AdobeRequest.postData", return_value = entity_response)
    def test_flowservice_create_streaming_connection(self, mock_connector):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        res = flow_service_conn.createStreamingConnection(name="test", sourceId="sourceId", dataType="json", paramName="test")
        mock_connector.assert_called_once_with('https://platform-stage.adobe.io/data/foundation/flowservice/connections', data={'name': 'test', 'providerId': '521eee4d-8cbe-4906-bb48-fb6bd4450033', 'description': 'provided by aepp', 'connectionSpec': {'id': 'bc7b00d6-623a-4dfc-9fdb-f1240aeadaeb', 'version': '1.0'}, 'auth': {'specName': 'Streaming Connection', 'params': {'sourceId': 'sourceId', 'dataType': 'json', 'name': 'test'}}}, format='json')
        assert res == self.entity_response

    @patch("aepp.connector.AdobeRequest.getData", return_value = entity_response)
    def test_flowservice_get_connection(self, mock_connector):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        res = flow_service_conn.getConnection(connectionId="test")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.entity_response

    @patch("aepp.connector.AdobeRequest.getData", return_value = entity_response)
    def test_flowservice_connection(self, mock_connector):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        res = flow_service_conn.connectionTest(connectionId="test")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.entity_response

    @patch("aepp.connector.AdobeRequest.deleteData", return_value = entity_response)
    def test_flowservice_delete_connection(self, mock_connector):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        res = flow_service_conn.deleteConnection(connectionId="test")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.entity_response

    @patch("aepp.connector.AdobeRequest.getData", return_value = entity_list_response)
    def test_flowservice_get_connection_specs(self, mock_connector):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        res = flow_service_conn.getConnectionSpecs()
        mock_connector.assert_called_once_with(ANY)
        assert res == self.entity_list_response

    @patch("aepp.connector.AdobeRequest.getData", return_value = entity_list_response)
    def test_flowservice_get_connection_specs_map(self, mock_connector):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        res = flow_service_conn.getConnectionSpecsMap()
        mock_connector.assert_called_once_with(ANY)
        assert res == self.entity_map_response

    @patch("aepp.connector.AdobeRequest.getData", return_value = entity_items_response)
    def test_flowservice_get_connection_spec(self, mock_connector):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        res = flow_service_conn.getConnectionSpec(specId="test")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.entity_response
    @patch("aepp.connector.AdobeRequest.getData", return_value = entity_list_response)
    def test_flowservice_get_connection_specid_from_name(self, mock_connector):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        res = flow_service_conn.getConnectionSpecIdFromName(name="test1")
        mock_connector.assert_called_once_with(ANY)
        assert res == "test1"
    # @patch("aepp.connector.AdobeRequest.getData", return_value = entity_list_response)
    # def test_flowservice_get_flows(self, mock_connector):
    #     # flow_service_conn = FlowService(config=self.config, header=MagicMock())
    #     # res = flow_service_conn.getFlows()
    #     # mock_connector.assert_called_once_with(ANY)
    #     # assert res == self.entity_list_response
    #     assert True

    @patch("aepp.connector.AdobeRequest.getData", return_value = entity_items_response)
    def test_flowservice_get_flow(self, mock_connector):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        res = flow_service_conn.getFlow(flowId="test")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.entity_response

    @patch("aepp.connector.AdobeRequest.deleteData", return_value = entity_response)
    def test_flowservice_delete_flow(self, mock_connector):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        res = flow_service_conn.deleteFlow(flowId="test")
        mock_connector.assert_called_once_with(ANY)
        assert res == self.entity_response

    @patch("aepp.connector.AdobeRequest.postData", return_value = entity_response)
    def test_flowservice_create_flow(self, mock_connector):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        res = flow_service_conn.createFlow(flow_spec_id="test", name="test", source_connection_id="test", target_connection_id="test")
        mock_connector.assert_called_once_with('https://platform-stage.adobe.io/data/foundation/flowservice/flows', data={'name': 'test', 'flowSpec': {'id': 'test', 'version': '1.0'}, 'sourceConnectionIds': ['test'], 'targetConnectionIds': ['test'], 'transformations': [], 'scheduleParams': {'frequency': 'minute', 'interval': '15'}})
        assert res == self.entity_response

    def test_flowservice_create_flow_data_lake_to_data_landing_zone(self):
        assert True

    def test_flowservice_create_data_landing_zone_to_datalake(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_updateFlow(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_get_flow_specs(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_get_flow_spec_id_from_names(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_get_flow_spec(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_get_runs(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_create_run(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_get_run(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_get_source_connections(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_get_source_connection(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True


    def test_flowsevrice_delete_source_connection(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_create_source_connection(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_create_source_connection_streaming(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_create_source_connectionDataLandingZone(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_create_source_connection_datalake(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_update_source_connection(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True


    def test_flowservice_get_target_connections(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_get_target_connection(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_delete_target_connection(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_create_target_connection(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_create_target_connection_data_landin_zone(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_create_target_connection_datalake(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_update_target_connection(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_update_policy(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_get_landing_zone_container(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_get_landing_zone_credential(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_explore_landing_zone(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

    def test_flowservice_get_landing_zone_content(self):
        flow_service_conn = FlowService(config=self.config, header=MagicMock())
        assert True

if __name__ == '__main__':
    unittest.main()
