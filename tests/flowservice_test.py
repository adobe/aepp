#  Copyright 2023 Adobe. All rights reserved.
#  This file is licensed to you under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License. You may obtain a copy
#  of the License at http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software distributed under
#  the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
#  OF ANY KIND, either express or implied. See the License for the specific language
#  governing permissions and limitations under the License.

from aepp.schema import Schema
from aepp.flowservice import FlowService
import unittest
from unittest.mock import patch, MagicMock


class FlowserviceTest(unittest.TestCase):

    def test_flowservice_get_resource(self):
        assert True

    def test_flowservice_get_connections(self):
        assert True

    def test_flowservice_create_connection(self):
        assert True

    def test_flowservice_create_streaming_connection(self):
        assert True

    def test_flowservice_get_connection(self):
        assert True

    def test_flowservice_connection(self):
        assert True

    def test_flowservice_delete_connection(self):
        assert True

    def test_flowservice_get_connection_specs(self):
        assert True

    def test_flowservice_get_connection_specs_map(self):
        assert True

    def test_flowservice_get_connection_spec(self):
        assert True

    def test_flowservice_get_connection_specid_from_name(self):
        assert True

    def test_flowservice_get_flows(self):
        assert True

    def test_flowservice_get_flow(self):
        assert True

    def test_flowservice_delete_flow(self):
        assert True

    def test_flowservice_create_flow(self):
        assert True

    def test_flowservice_create_flow_data_lake_to_data_landing_zone(self):
        assert True

    def test_flowservice_create_data_landing_zone_to_datalake(self):
        assert True

    def test_flowservice_updateFlow(self):
        assert True

    def test_flowservice_get_flow_specs(self):
        assert True

    def test_flowservice_get_flow_spec_id_from_names(self):
         assert True

    def test_flowservice_get_flow_spec(self):
        assert True

    def test_flowservice_get_runs(self):
        assert True

    @patch("aepp.connector.AdobeRequest")
    def test_flowservice_create_run_default(self, mock_connector):
        instance_conn = mock_connector.return_value
        instance_conn.postData.return_value = {"id": "run-123"}
        flow_service = FlowService()
        result = flow_service.createRun(flowId="flow-abc")
        self.assertEqual(result, {"id": "run-123"})
        instance_conn.postData.assert_called_with(
            flow_service.endpoint + "/runs",
            data={"flowId": "flow-abc", "status": "active"}
        )

    @patch("aepp.connector.AdobeRequest")
    def test_flowservice_create_run_with_params(self, mock_connector):
        instance_conn = mock_connector.return_value
        instance_conn.postData.return_value = {"id": "run-123"}
        flow_service = FlowService()
        params = {
            "startTime": 1640995200,
            "windowStartTime": 1640908800,
            "windowEndTime": 1640995200
        }
        result = flow_service.createRun(flowId="flow-abc", status="active", params=params)
        self.assertEqual(result, {"id": "run-123"})
        instance_conn.postData.assert_called_with(
            flow_service.endpoint + "/runs",
            data={"flowId": "flow-abc", "status": "active", "params": params}
        )

    @patch("aepp.connector.AdobeRequest")
    def test_flowservice_create_run_missing_flowid(self, mock_connector):
        flow_service = FlowService()
        with self.assertRaises(Exception) as cm:
            flow_service.createRun(flowId=None)
        self.assertIn("Require a flowId", str(cm.exception))

    def test_flowservice_get_run(self):
        assert True

    def test_flowservice_get_source_connections(self):
        assert True

    def test_flowservice_get_source_connection(self):
        assert True


    def test_flowsevrice_delete_source_connection(self):
        assert True

    def test_flowservice_create_source_connection(self):
        assert True

    def test_flowservice_create_source_connection_streaming(self):
        assert True

    def test_flowservice_create_source_connectionDataLandingZone(self):
        assert True

    def test_flowservice_create_source_connection_datalake(self):
        assert True

    def test_flowservice_update_source_connection(self):
        assert True


    def test_flowservice_get_target_connections(self):
        assert True

    def test_flowservice_get_target_connection(self):
        assert True

    def test_flowservice_delete_target_connection(self):
        assert True

    def test_flowservice_create_target_connection(self):
        assert True

    def test_flowservice_create_target_connection_data_landin_zone(self):
        assert True

    def test_flowservice_create_target_connection_datalake(self):
        assert True

    def test_flowservice_update_target_connection(self):
        assert True

    def test_flowservice_update_policy(self):
        assert True

    def test_flowservice_get_landing_zone_container(self):
        assert True

    def test_flowservice_get_landing_zone_credential(self):
        assert True

    def test_flowservice_explore_landing_zone(self):
        assert True

    def test_flowservice_get_landing_zone_content(self):
        assert True
