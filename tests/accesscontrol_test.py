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

class AccessControlTest(unittest.TestCase):
    @patch("aepp.connector.AdobeRequest.getData", return_value = MagicMock())
    def test_get_reference(self, mock_connector):
        access_control_instance = AccessControl(config=MagicMock(), header=MagicMock())
        access_control_instance.getReferences()

    def test_post_effective_policies_with_invalid_input(self):
        access_control_instance = AccessControl(config=MagicMock(), header=MagicMock())
        try:
            access_control_instance.postEffectivePolicies(listElements="test")
            self.fail("expect a type error")
        except TypeError:
            pass

    @patch("aepp.connector.AdobeRequest.postData", return_value = {"result"})
    def test_post_effective_policies(self, mock_connector):
        access_control_instance = AccessControl(config=MagicMock(), header=MagicMock())
        result = access_control_instance.postEffectivePolicies(["test"])
        assert (result == {"result"})


if __name__ == '__main__':
    unittest.main()
